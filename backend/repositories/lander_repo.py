"""
Repository: Lander
CRUD da tabela lander. Services chamam estas funções — nunca session.exec() diretamente.
"""

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.lander import Lander


async def get_by_id(session: AsyncSession, lander_id: int) -> Optional[Lander]:
    return await session.get(Lander, lander_id)


async def list_all(session: AsyncSession) -> list[Lander]:
    result = await session.exec(select(Lander))
    return list(result.all())


async def create(session: AsyncSession, **kwargs) -> Lander:
    lander = Lander(**kwargs)
    session.add(lander)
    await session.flush()  # Gera o ID sem fechar a transação
    return lander


async def update(session: AsyncSession, lander: Lander, **kwargs) -> Lander:
    for key, value in kwargs.items():
        setattr(lander, key, value)
    session.add(lander)
    await session.flush()
    return lander
