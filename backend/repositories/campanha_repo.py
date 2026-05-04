"""
Repository: Campanha e TrafficChannel
"""

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.campanha import Campanha
from backend.models.traffic import TrafficChannel


async def get_traffic_channel_by_nome(
    session: AsyncSession, nome: str
) -> Optional[TrafficChannel]:
    result = await session.exec(
        select(TrafficChannel).where(TrafficChannel.nome == nome)
    )
    return result.first()


async def create_traffic_channel(
    session: AsyncSession, nome: str, identificador_api: str
) -> TrafficChannel:
    tc = TrafficChannel(nome=nome, identificador_api=identificador_api)
    session.add(tc)
    await session.flush()
    return tc


async def get_or_create_traffic_channel_local(
    session: AsyncSession, nome: str, identificador_api: str
) -> TrafficChannel:
    """Busca ou cria o TrafficChannel no banco local."""
    tc = await get_traffic_channel_by_nome(session, nome)
    if not tc:
        tc = await create_traffic_channel(session, nome, identificador_api)
    return tc


async def create_campanha(
    session: AsyncSession,
    lander_id: int,
    traffic_channel_id: int,
    nome: str,
    redtrack_campaign_id: str,
    url_cloaker: str,
) -> Campanha:
    campanha = Campanha(
        lander_id=lander_id,
        traffic_channel_id=traffic_channel_id,
        nome=nome,
        redtrack_campaign_id=redtrack_campaign_id,
        url_cloaker=url_cloaker,
    )
    session.add(campanha)
    await session.flush()
    return campanha


async def list_all(session: AsyncSession) -> list[Campanha]:
    result = await session.exec(select(Campanha))
    return list(result.all())
