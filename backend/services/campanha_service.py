"""
Service: Campanha
Orquestra criação de campanha: validação da Lander, resolução de TrafficChannel,
criação no RedTrack e persistência no banco local.
"""

import logging

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.repositories import campanha_repo, lander_repo, produto_repo
from backend.schemas.campanha import CampanhaCreate, CampanhaRead
from backend.services import redtrack_service

logger = logging.getLogger(__name__)


async def create(session: AsyncSession, payload: CampanhaCreate) -> CampanhaRead:
    """
    Cria campanha completa no RedTrack.
    Fluxo:
    1. Valida Lander e verifica se está deployada
    2. Resolve/cria TrafficChannel no RedTrack e localmente
    3. Cria campanha no RedTrack via API
    4. Persiste e retorna url_cloaker
    """
    lander = await lander_repo.get_by_id(session, payload.lander_id)
    if not lander:
        raise HTTPException(status_code=404, detail=f"Lander ID {payload.lander_id} não encontrada.")
    if not lander.redtrack_lander_id:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Lander ID {payload.lander_id} ainda não foi registrada no RedTrack. "
                "Realize o deploy antes de criar a campanha."
            ),
        )

    dominio = await produto_repo.get_dominio_by_id(session, lander.dominio_id)
    if not dominio:
        raise HTTPException(status_code=500, detail="Domínio da lander não encontrado.")

    # Resolve ou cria Traffic Channel no RedTrack
    try:
        rt_channel_id = await redtrack_service.get_or_create_traffic_channel(
            payload.traffic_channel_nome
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao resolver Traffic Channel no RedTrack: {e}",
        )

    # Garante TrafficChannel no banco local
    tc = await campanha_repo.get_or_create_traffic_channel_local(
        session, payload.traffic_channel_nome, rt_channel_id
    )

    # Cria campanha no RedTrack
    try:
        rt_result = await redtrack_service.create_campaign(
            nome=payload.nome,
            lander_id=lander.redtrack_lander_id,
            traffic_channel_id=rt_channel_id,
            tracking_domain=dominio.url,
            postback_url=payload.postback_url,
            prelander_id=payload.prelander_redtrack_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar campanha no RedTrack: {e}",
        )

    campanha = await campanha_repo.create_campanha(
        session,
        lander_id=payload.lander_id,
        traffic_channel_id=tc.id,
        nome=payload.nome,
        redtrack_campaign_id=rt_result["campaign_id"],
        url_cloaker=rt_result["url_cloaker"],
    )

    logger.info(
        f"Campanha criada: '{campanha.nome}' | RT ID: {campanha.redtrack_campaign_id} | "
        f"Cloaker: {campanha.url_cloaker}"
    )

    return CampanhaRead(
        id=campanha.id,
        nome=campanha.nome,
        lander_id=campanha.lander_id,
        traffic_channel_id=campanha.traffic_channel_id,
        redtrack_campaign_id=campanha.redtrack_campaign_id,
        url_cloaker=campanha.url_cloaker,
    )


async def list_all(session: AsyncSession) -> list[CampanhaRead]:
    campanhas = await campanha_repo.list_all(session)
    return [
        CampanhaRead(
            id=c.id,
            nome=c.nome,
            lander_id=c.lander_id,
            traffic_channel_id=c.traffic_channel_id,
            redtrack_campaign_id=c.redtrack_campaign_id,
            url_cloaker=c.url_cloaker,
        )
        for c in campanhas
    ]
