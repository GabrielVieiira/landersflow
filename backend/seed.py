#!/usr/bin/env python
"""
backend/seed.py
Script de seed para popular o banco de dados de desenvolvimento.

Execução:
    poetry run python -m backend.seed
"""

import asyncio
import logging
import sys

from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ===========================================================================
# 1. NICHOS
# ===========================================================================

NICHOS = [
    # (sigla, nome)
    ("EMAG", "Emagrecimento"),
    ("TT",   "Tinnitus"),
    ("ML",   "Memory Loss"),
    ("T2D",  "Type 2 Diabetes"),
    ("ED",   "Erectile Dysfunction"),
    ("PT",   "Próstata"),
    ("NPT",  "Neuropatia"),
    ("VIS",  "Visão"),
]

# ===========================================================================
# 2. PLATAFORMAS DE CHECKOUT
# ===========================================================================

PLATAFORMAS = [
    # (nome, slug_aplicacao, integra_redtrack_offer, padrao_link_html)
    (
        "ClickBank",
        "clickbank",
        False,
        'href="{url_checkout}"',
    ),
    (
        "CartPanda",
        "cartpanda",
        True,
        'href="#" data-click-path="/click/{qtd}"',
    ),
]

# ===========================================================================
# 3. PRODUTOS
# Cores: tons de verde para primária, amarelo-âmbar para secundária, branco fundo.
# Paleta harmônica por produto (consistente entre plataformas).
# ===========================================================================

_CORES = {
    # produto_nome: (cor_primaria, cor_secundaria)
    "Echozen":    ("#2E7D32", "#F9A825"),   # verde-floresta + âmbar
    "BrainHoney": ("#33691E", "#F57F17"),   # verde-oliva + laranja-âmbar
    "Jellyburn":  ("#1B5E20", "#FFB300"),   # verde-escuro + dourado
    "VisiumMax":  ("#388E3C", "#FDD835"),   # verde-médio + amarelo
    "Prostaflow": ("#1A6B3C", "#F0C040"),   # verde-esmeralda + amarelo-quente
    "Nervetin":   ("#27AE60", "#F1C40F"),   # esmeralda + amarelo-brilhante
}

PRODUTOS = []
for nicho_id, plataforma_id, nome in [
    # ClickBank (plataforma_id=1)
    (2, 1, "Echozen"),
    (3, 1, "BrainHoney"),
    (1, 1, "Jellyburn"),
    (8, 1, "VisiumMax"),
    (6, 1, "Prostaflow"),
    (7, 1, "Nervetin"),
    # CartPanda (plataforma_id=2)
    (2, 2, "Echozen"),
    (3, 2, "BrainHoney"),
    (1, 2, "Jellyburn"),
    (8, 2, "VisiumMax"),
    (6, 2, "Prostaflow"),
    (7, 2, "Nervetin"),
]:
    PRODUTOS.append({
        "nicho_id_direto":       nicho_id,   # ID direto (sem lookup por sigla)
        "plataforma_id_direto":  plataforma_id,
        "nome":                  nome,
        "cor_primaria":          _CORES[nome][0],
        "cor_secundaria":        _CORES[nome][1],
        "cor_background":        "#FFFFFF",
    })


# ===========================================================================
# 4. PRODUTO_CHECKOUT_PARAM
# Apenas para produtos ClickBank (produtos 1–6 na ordem acima).
# Mapeado por índice interno (0-based) dentro do slice ClickBank.
# ===========================================================================

# Formato: (produto_index_0based, chave, valor)
# produto_index 0 = Echozen/CB, 1 = BrainHoney/CB, ..., 5 = Nervetin/CB
CHECKOUT_PARAMS_CB = [
    (0, "vendor", "echozenn"),
    (1, "vendor", "2brainhone"),
    (2, "vendor", "jellyburrn"),
    (3, "vendor", "visiummaxx"),
    (4, "vendor", "prostafloo"),
    (5, "vendor", "nervetinn"),
]


# ===========================================================================
# 5. PRODUTO_VARIACAO
# url_imagem: deixado vazio — preencha com as URLs de imagem de cada produto.
# ===========================================================================

_IMG = ""  # placeholder — atualize com as URLs reais depois

VARIACOES = [
    # (produto_index_0based, quantidade_potes, checkout_identifier, url_imagem)
    # --- Echozen / ClickBank (produto 0) ---
    (0, 2, "https://echozenn.pay.clickbank.net/?cbitems=FE-ECZ-02B-D&cbfid=62916&template=2bottles&param=vsl", _IMG),
    (0, 3, "https://echozenn.pay.clickbank.net/?cbitems=FE-ECZ-03B-D&cbfid=62917&template=3bottles&param=vsl", _IMG),
    (0, 6, "https://echozenn.pay.clickbank.net/?cbitems=FE-ECZ-06B-D&cbfid=62918&template=6bottles&param=vsl", _IMG),
    # --- BrainHoney / ClickBank (produto 1) ---
    (1, 2, "https://2brainhone.pay.clickbank.net/?cbitems=FE-BHY-02B-C&cbfid=62889&template=2bottles&param=vsl", _IMG),
    (1, 3, "https://2brainhone.pay.clickbank.net/?cbitems=FE-BHY-03B-C&cbfid=62890&template=3bottles&param=vsl", _IMG),
    (1, 6, "https://2brainhone.pay.clickbank.net/?cbitems=FE-BHY-06B-C&cbfid=62891&template=6bottles&param=vsl", _IMG),
    # --- Jellyburn / ClickBank (produto 2) ---
    (2, 2, "https://jellyburrn.pay.clickbank.net/?cbitems=FE-JEB-02B-D&cbfid=62901&template=2bottles&param=vsl", _IMG),
    (2, 3, "https://jellyburrn.pay.clickbank.net/?cbitems=FE-JEB-03B-D&cbfid=62902&template=3bottles&param=vsl", _IMG),
    (2, 6, "https://jellyburrn.pay.clickbank.net/?cbitems=FE-JEB-06B-D&cbfid=62923&template=6bottles&param=vsl", _IMG),
    # --- VisiumMax / ClickBank (produto 3) ---
    (3, 2, "https://visiummaxx.pay.clickbank.net/?cbitems=FE-VSM-02B-D&cbfid=62980&template=2bottles&param=vsl", _IMG),
    (3, 3, "https://visiummaxx.pay.clickbank.net/?cbitems=FE-VSM-03B-D&cbfid=62981&template=3bottles&param=vsl", _IMG),
    (3, 6, "https://visiummaxx.pay.clickbank.net/?cbitems=FE-VSM-06B-D&cbfid=62982&template=6bottles&param=vsl", _IMG),
    # --- Prostaflow / ClickBank (produto 4) ---
    (4, 2, "https://prostafloo.pay.clickbank.net/?cbitems=FE-PFW-02B-C&cbfid=62995&template=2bottles&param=vsl", _IMG),
    (4, 3, "https://prostafloo.pay.clickbank.net/?cbitems=FE-PFW-03B-C&cbfid=62996&template=3bottles&param=vsl", _IMG),
    (4, 6, "https://prostafloo.pay.clickbank.net/?cbitems=FE-PFW-06B-C&cbfid=62997&template=6bottles&param=vsl", _IMG),
    # --- Nervetin / ClickBank (produto 5) ---
    (5, 2, "https://nervetinn.pay.clickbank.net/?cbitems=FE-NVT-02B-C&cbfid=62910&template=2bottles&param=vsl", _IMG),
    (5, 3, "https://nervetinn.pay.clickbank.net/?cbitems=FE-NVT-03B-C&cbfid=62967&template=3bottles&param=vsl", _IMG),
    (5, 6, "https://nervetinn.pay.clickbank.net/?cbitems=FE-NVT-06B-C&cbfid=62968&template=6bottles&param=vsl", _IMG),
    # --- Echozen / CartPanda (produto 6) — IDs da CartPanda ---
    (6, 2, "1", _IMG),
    (6, 3, "3", _IMG),
    (6, 6, "2", _IMG),
    # --- BrainHoney / CartPanda (produto 7) ---
    (7, 2, "1", _IMG),
    (7, 3, "3", _IMG),
    (7, 6, "2", _IMG),
    # --- Jellyburn / CartPanda (produto 8) ---
    (8, 2, "1", _IMG),
    (8, 3, "3", _IMG),
    (8, 6, "2", _IMG),
    # --- VisiumMax / CartPanda (produto 9) ---
    (9, 2, "1", _IMG),
    (9, 3, "3", _IMG),
    (9, 6, "2", _IMG),
    # --- Prostaflow / CartPanda (produto 10) ---
    (10, 2, "1", _IMG),
    (10, 3, "3", _IMG),
    (10, 6, "2", _IMG),
    # --- Nervetin / CartPanda (produto 11) ---
    (11, 2, "1", _IMG),
    (11, 3, "3", _IMG),
    (11, 6, "2", _IMG),
]


# ===========================================================================
# 6. TIPOS DE TEMPLATE
# ===========================================================================

TIPOS_TEMPLATE = [
    # (id, nome)
    (1, "lander"),
    (2, "offer_section"),
]


# ===========================================================================
# 7. TEMPLATES
# ===========================================================================

TEMPLATES = [
    # (id, nome, tipo_id, repo_github)
    (1, "cnn",    1, "lander/cnn"),
    (2, "fox",    1, "lander/fox"),
    (3, "today",  1, "lander/today"),
    (4, "padrao", 2, "offer_section/padrao"),
    (5, "quiz",   2, "offer_section/quiz"),
]


# ===========================================================================
# ENGINE
# ===========================================================================

def _get_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from backend.config import get_settings
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )


# ===========================================================================
# SEED FUNCTION
# ===========================================================================

async def _seed(session: AsyncSession) -> None:
    from backend.models.plataforma import Nicho, PlataformaCheckout
    from backend.models.produto import Produto, ProdutoVariacao, ProdutoCheckoutParam
    from backend.models.template import TipoTemplate, Template

    # -------------------------------------------------------------------
    # 1. Nichos
    # -------------------------------------------------------------------
    log.info("Inserindo Nichos...")
    nicho_ids: list[int] = []
    for sigla, nome in NICHOS:
        obj = Nicho(sigla=sigla, nome=nome)
        session.add(obj)
        await session.flush()
        nicho_ids.append(obj.id)
        log.info(f"  [{obj.id}] {sigla} — {nome}")

    # -------------------------------------------------------------------
    # 2. Plataformas de Checkout
    # -------------------------------------------------------------------
    log.info("Inserindo Plataformas de Checkout...")
    plataforma_ids: list[int] = []
    for nome, slug, integra, padrao in PLATAFORMAS:
        obj = PlataformaCheckout(
            nome=nome,
            slug_aplicacao=slug,
            integra_redtrack_offer=integra,
            padrao_link_html=padrao,
        )
        session.add(obj)
        await session.flush()
        plataforma_ids.append(obj.id)
        log.info(f"  [{obj.id}] {nome} (slug: {slug})")

    # -------------------------------------------------------------------
    # 3. Produtos
    # -------------------------------------------------------------------
    log.info("Inserindo Produtos...")
    produto_ids: list[int] = []

    for p in PRODUTOS:
        # Converte índice 1-based dos dados para ID real do banco
        nicho_db_id   = nicho_ids[p["nicho_id_direto"] - 1]
        plat_db_id    = plataforma_ids[p["plataforma_id_direto"] - 1]

        obj = Produto(
            nicho_id=nicho_db_id,
            plataforma_checkout_id=plat_db_id,
            nome=p["nome"],
            cor_primaria=p["cor_primaria"],
            cor_secundaria=p["cor_secundaria"],
            cor_background=p["cor_background"],
        )
        session.add(obj)
        await session.flush()
        produto_ids.append(obj.id)
        log.info(f"  [{obj.id}] {p['nome']} | plat={plat_db_id} nicho={nicho_db_id} | {p['cor_primaria']}/{p['cor_secundaria']}")

    # -------------------------------------------------------------------
    # 4. Checkout Params (apenas produtos ClickBank, índices 0–5)
    # -------------------------------------------------------------------
    log.info("Inserindo Checkout Params (ClickBank)...")
    for prod_idx, chave, valor in CHECKOUT_PARAMS_CB:
        obj = ProdutoCheckoutParam(
            produto_id=produto_ids[prod_idx],
            chave=chave,
            valor=valor,
        )
        session.add(obj)
        log.info(f"  produto_id={produto_ids[prod_idx]} | {chave}={valor}")

    await session.flush()

    # -------------------------------------------------------------------
    # 5. Variações
    # -------------------------------------------------------------------
    log.info("Inserindo Variações...")
    for prod_idx, qtd, checkout_id, img_url in VARIACOES:
        obj = ProdutoVariacao(
            produto_id=produto_ids[prod_idx],
            quantidade_potes=qtd,
            checkout_identifier=checkout_id,
            url_imagem=img_url,
        )
        session.add(obj)
        log.info(f"  produto_id={produto_ids[prod_idx]} | {qtd} potes | {checkout_id[:50]}...")

    await session.flush()

    # -------------------------------------------------------------------
    # 6. Tipos de Template
    # -------------------------------------------------------------------
    log.info("Inserindo Tipos de Template...")
    for tipo_id, tipo_nome in TIPOS_TEMPLATE:
        obj = TipoTemplate(id=tipo_id, nome=tipo_nome)
        session.add(obj)
        log.info(f"  [{tipo_id}] {tipo_nome}")
    await session.flush()

    # -------------------------------------------------------------------
    # 7. Templates
    # -------------------------------------------------------------------
    log.info("Inserindo Templates...")
    for tmpl_id, tmpl_nome, tipo_id, repo in TEMPLATES:
        tipo_nome = next(n for i, n in TIPOS_TEMPLATE if i == tipo_id)
        obj = Template(id=tmpl_id, nome=tmpl_nome, tipo_template_id=tipo_id, repo_github=repo)
        session.add(obj)
        log.info(f"  [{tmpl_id}] {tmpl_nome} ({tipo_nome}) | {repo}")
    await session.flush()

    await session.commit()
    log.info("=" * 60)
    log.info("SEED CONCLUIDO COM SUCESSO!")
    log.info(f"  {len(NICHOS)} nichos")
    log.info(f"  {len(PLATAFORMAS)} plataformas")
    log.info(f"  {len(PRODUTOS)} produtos")
    log.info(f"  {len(CHECKOUT_PARAMS_CB)} checkout params")
    log.info(f"  {len(VARIACOES)} variações")
    log.info(f"  {len(TIPOS_TEMPLATE)} tipos de template")
    log.info(f"  {len(TEMPLATES)} templates")
    log.info("=" * 60)


# ===========================================================================
# MAIN
# ===========================================================================

async def main() -> None:
    # Registra todos os models no metadata antes de criar tabelas
    from backend.models.plataforma import Nicho, PlataformaCheckout  # noqa
    from backend.models.dominio import Dominio  # noqa
    from backend.models.template import TipoTemplate, Template  # noqa
    from backend.models.traffic import TrafficChannel, TrafficChannelPostback  # noqa
    from backend.models.produto import Produto, ProdutoVariacao, ProdutoCheckoutParam  # noqa
    from backend.models.lander import Lander  # noqa
    from backend.models.campanha import Campanha  # noqa

    engine = _get_engine()

    # Garante que todas as tabelas existam
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    log.info("Tabelas verificadas/criadas.")

    from sqlalchemy.orm import sessionmaker
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        await _seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
