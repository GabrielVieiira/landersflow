"""
Repository: Template e TipoTemplate
Queries das tabelas template e tipo_template.
"""

from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.template import Template, TipoTemplate


async def get_tipo_by_id(session: AsyncSession, tipo_id: int) -> Optional[TipoTemplate]:
    return await session.get(TipoTemplate, tipo_id)


async def list_tipos(session: AsyncSession) -> list[TipoTemplate]:
    result = await session.exec(select(TipoTemplate))
    return list(result.all())


async def get_by_id(session: AsyncSession, template_id: int) -> Optional[Template]:
    return await session.get(Template, template_id)


async def list_all(
    session: AsyncSession,
    tipo_template_id: Optional[int] = None,
) -> list[Template]:
    query = select(Template)
    if tipo_template_id is not None:
        query = query.where(Template.tipo_template_id == tipo_template_id)
    result = await session.exec(query)
    return list(result.all())


async def create(
    session: AsyncSession,
    nome: str,
    tipo_template_id: int,
    repo_github: str,
) -> Template:
    template = Template(nome=nome, tipo_template_id=tipo_template_id, repo_github=repo_github)
    session.add(template)
    await session.flush()
    return template


async def delete(session: AsyncSession, template: Template) -> None:
    await session.delete(template)
    await session.flush()
