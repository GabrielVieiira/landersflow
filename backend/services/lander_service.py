"""
Service: Lander
Orquestra compilação, deploy e registro das Landing Pages.

Responsabilidades:
- Validar entidades (nicho, domínio, produto, templates) via repositories
- Chamar o compilador Jinja2 (compiler.py)
- Persistir via lander_repo
- Disparar background task de deploy
- Integrar GitHub + RedTrack

NÃO conhece HTTP — recebe e retorna objetos Python/Pydantic.
NÃO executa queries SQL diretamente — usa os repositories.
"""

import logging

from fastapi import BackgroundTasks, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import get_settings
from backend.database import AsyncSessionLocal
from backend.repositories import lander_repo, produto_repo, template_repo
from backend.schemas.lander import (
    CompileLanderRequest,
    CompileLanderResponse,
    DeployStatusResponse,
    LanderListItem,
)
from backend.services import compiler as compiler_svc
from backend.services import github_service, redtrack_service

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# COMPILE
# =============================================================================

async def compile(
    session: AsyncSession, payload: CompileLanderRequest
) -> CompileLanderResponse:
    """
    Valida entidades, compila os templates via Jinja2 e persiste a Lander.
    Não realiza deploy — apenas retorna os HTMLs para QA visual.
    """

    # 1. Valida nicho
    nicho = await produto_repo.get_nicho_by_id(session, payload.nicho_id)
    if not nicho:
        raise HTTPException(status_code=404, detail=f"Nicho ID {payload.nicho_id} não encontrado.")
    if nicho.sigla not in settings.nichos_lista:
        raise HTTPException(
            status_code=422,
            detail=f"Nicho '{nicho.sigla}' não está nos nichos permitidos: {settings.nichos_lista}",
        )

    # 2. Valida domínio
    dominio = await produto_repo.get_dominio_by_id(session, payload.dominio_id)
    if not dominio:
        raise HTTPException(status_code=404, detail=f"Domínio ID {payload.dominio_id} não encontrado.")

    # 3. Carrega produto + plataforma + variações (repo levanta 404/500 se não encontrar)
    produto, plataforma, variacoes = await produto_repo.get_with_relations(
        session, payload.produto_id
    )

    # Valida variações mínimas (2, 3 e 6 potes são exigidos pela doc)
    required = {2, 3, 6}
    missing = required - set(variacoes.keys())
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Produto ID {payload.produto_id} não possui variações para: {sorted(missing)} potes. "
                "Cadastre-as antes de compilar."
            ),
        )

    # 4. Busca templates no banco e conteúdo HTML no GitHub
    index_template = await template_repo.get_by_id(session, payload.template_index_id)
    if not index_template:
        raise HTTPException(status_code=404, detail=f"Template index ID {payload.template_index_id} não encontrado.")

    offer_template = await template_repo.get_by_id(session, payload.template_offer_id)
    if not offer_template:
        raise HTTPException(status_code=404, detail=f"Template offer ID {payload.template_offer_id} não encontrado.")

    try:
        index_files = github_service.get_template_folder(index_template.repo_github)
        offer_files = github_service.get_template_folder(offer_template.repo_github)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar template no GitHub: {e}")

    # 5. Compila via Jinja2
    # Slug temporário para preview (ID ainda desconhecido neste momento)
    preview_slug = "preview"
    try:
        compiled_files = compiler_svc.compile_lander_pages(
            lander_slug=preview_slug,
            index_template_files=index_files,
            offer_template_files=offer_files,
            produto=produto,
            plataforma=plataforma,
            variacoes=variacoes,
            payload_data=payload.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na compilacao Jinja2: {e}")

    # Extrai os HTMLs compilados para o preview (apenas para retorno da API)
    compiled_index = compiled_files.get(f"{preview_slug}/index.html", "")
    compiled_offer = compiled_files.get(f"{preview_slug}/offer/index.html", "")
    if isinstance(compiled_index, bytes):
        compiled_index = compiled_index.decode("utf-8")
    if isinstance(compiled_offer, bytes):
        compiled_offer = compiled_offer.decode("utf-8")

    # 6. Persiste Lander (sem deploy ainda)
    delay_segundos = compiler_svc.parse_vturb_delay(payload.vturb_delay)
    lander = await lander_repo.create(
        session,
        produto_id=payload.produto_id,
        template_index_id=payload.template_index_id,
        template_offer_id=payload.template_offer_id,
        dominio_id=payload.dominio_id,
        headline=payload.headline,
        vturb_preload=payload.vturb_preload,
        vturb_script=payload.vturb_script,
        vturb_delay_segundos=delay_segundos,
    )

    logger.info(f"Lander ID {lander.id} compilada. Delay: {delay_segundos}s. Aguardando QA.")

    return CompileLanderResponse(
        lander_id=lander.id,
        vturb_delay_segundos=delay_segundos,
        html_index_preview=compiled_index,
        html_offer_preview=compiled_offer,
    )


# =============================================================================
# DEPLOY
# =============================================================================

async def deploy(
    session: AsyncSession, lander_id: int, background_tasks: BackgroundTasks
) -> DeployStatusResponse:
    """
    Inicia o deploy em background (não bloqueia o response HTTP).
    Retorna 202 imediatamente; status consultado via GET /landers/{id}.
    """
    lander = await lander_repo.get_by_id(session, lander_id)
    if not lander:
        raise HTTPException(status_code=404, detail=f"Lander ID {lander_id} não encontrada.")
    if lander.url_final:
        raise HTTPException(
            status_code=409,
            detail=f"Lander ID {lander_id} já foi deployada em: {lander.url_final}",
        )

    background_tasks.add_task(_run_deploy_background, lander_id)

    return DeployStatusResponse(
        lander_id=lander_id,
        url_final=None,
        redtrack_lander_id=None,
        status="deploying",
        message="Deploy iniciado em background. Consulte GET /landers/{id} para status.",
    )


async def _run_deploy_background(lander_id: int) -> None:
    """
    Task executada em background — cria sua própria sessão pois está fora
    do ciclo de vida do request HTTP.
    """
    async with AsyncSessionLocal() as session:
        try:
            lander = await lander_repo.get_by_id(session, lander_id)
            if not lander:
                logger.error(f"Lander {lander_id} não encontrada no deploy background.")
                return

            produto, plataforma, variacoes = await produto_repo.get_with_relations(
                session, lander.produto_id
            )
            dominio = await produto_repo.get_dominio_by_id(session, lander.dominio_id)

            index_template = await template_repo.get_by_id(session, lander.template_index_id)
            offer_template = await template_repo.get_by_id(session, lander.template_offer_id)

            index_files = github_service.get_template_folder(index_template.repo_github)
            offer_files = github_service.get_template_folder(offer_template.repo_github)

            # Reconstroi payload com dados do banco
            mins, secs = divmod(lander.vturb_delay_segundos, 60)
            payload_data = {
                "nome_produto": produto.nome,
                "headline": lander.headline,
                "vturb_preload": lander.vturb_preload,
                "vturb_script": lander.vturb_script,
                "vturb_delay": f"{mins:02d}:{secs:02d}",
            }

            # Slug: pasta no repo de destino (ex: 'lander-7')
            lander_slug = f"lander-{lander_id}"

            compiled_files = compiler_svc.compile_lander_pages(
                lander_slug=lander_slug,
                index_template_files=index_files,
                offer_template_files=offer_files,
                produto=produto,
                plataforma=plataforma,
                variacoes=variacoes,
                payload_data=payload_data,
            )

            dest_repo = dominio.url.replace(".", "-")
            github_service.deploy_lander_files(
                dest_repo,
                compiled_files,
                f"feat: deploy lander #{lander_id} - {produto.nome}"
            )

            url_final = f"https://{dominio.url}/{lander_slug}/"
            await lander_repo.update(session, lander, url_final=url_final)
            await session.commit()

            is_live = await redtrack_service.poll_url_until_live(
                url_final,
                timeout_seconds=settings.deploy_polling_timeout,
                interval_seconds=settings.deploy_polling_interval,
            )
            if not is_live:
                logger.error(f"Deploy timeout: {url_final} não ficou ativa.")
                return

            rt_lander_id = await redtrack_service.register_lander(
                name=f"{produto.nome} - Lander #{lander_id}",
                url=url_final,
                tracking_domain=dominio.url,
                listicle=plataforma.integra_redtrack_offer,
            )

            await lander_repo.update(session, lander, redtrack_lander_id=rt_lander_id)
            await session.commit()
            logger.info(f"✅ Deploy completo: Lander #{lander_id} | URL: {url_final} | RT: {rt_lander_id}")

        except Exception as e:
            logger.exception(f"❌ Erro no deploy da Lander #{lander_id}: {e}")


# =============================================================================
# QUERIES (READ)
# =============================================================================

async def list_landers(session: AsyncSession) -> list[LanderListItem]:
    landers = await lander_repo.list_all(session)
    items = []
    for lander in landers:
        produto = await produto_repo.get_by_id(session, lander.produto_id)
        items.append(
            LanderListItem(
                id=lander.id,
                produto_nome=produto.nome if produto else "—",
                headline=lander.headline,
                url_final=lander.url_final,
                redtrack_lander_id=lander.redtrack_lander_id,
                vturb_delay_segundos=lander.vturb_delay_segundos,
            )
        )
    return items


async def get_status(session: AsyncSession, lander_id: int) -> DeployStatusResponse:
    lander = await lander_repo.get_by_id(session, lander_id)
    if not lander:
        raise HTTPException(status_code=404, detail=f"Lander ID {lander_id} não encontrada.")

    if lander.url_final and lander.redtrack_lander_id:
        status, msg = "live", f"Lander ativa em {lander.url_final}"
    elif lander.url_final:
        status, msg = "deploying", "Deployada, aguardando registro no RedTrack."
    else:
        status, msg = "pending", "Aguardando QA e deploy."

    return DeployStatusResponse(
        lander_id=lander_id,
        url_final=lander.url_final,
        redtrack_lander_id=lander.redtrack_lander_id,
        status=status,
        message=msg,
    )
