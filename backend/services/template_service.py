"""
Service: Template
CRUD de Templates HTML com validação de tipo.
"""

import logging

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.repositories import template_repo
from backend.schemas.template import TemplateCreate, TemplateRead, TipoTemplateRead

logger = logging.getLogger(__name__)


async def list_tipos(session: AsyncSession) -> list[TipoTemplateRead]:
    tipos = await template_repo.list_tipos(session)
    return [TipoTemplateRead(id=t.id, nome=t.nome) for t in tipos]


async def create(session: AsyncSession, payload: TemplateCreate) -> TemplateRead:
    # Valida que o tipo_template_id existe
    tipo = await template_repo.get_tipo_by_id(session, payload.tipo_template_id)
    if not tipo:
        raise HTTPException(
            status_code=422,
            detail=f"tipo_template_id {payload.tipo_template_id} não encontrado."
        )

    template = await template_repo.create(
        session,
        nome=payload.nome,
        tipo_template_id=payload.tipo_template_id,
        repo_github=payload.repo_github,
    )
    logger.info(f"Template criado: '{template.nome}' (ID: {template.id}, tipo: {tipo.nome})")
    return TemplateRead(
        id=template.id,
        nome=template.nome,
        tipo_template_id=template.tipo_template_id,
        repo_github=template.repo_github,
        tipo_nome=tipo.nome,
    )


async def list_all(
    session: AsyncSession,
    tipo_template_id: int | None = None,
) -> list[TemplateRead]:
    templates = await template_repo.list_all(session, tipo_template_id=tipo_template_id)
    result = []
    for t in templates:
        tipo = await template_repo.get_tipo_by_id(session, t.tipo_template_id)
        result.append(TemplateRead(
            id=t.id,
            nome=t.nome,
            tipo_template_id=t.tipo_template_id,
            repo_github=t.repo_github,
            tipo_nome=tipo.nome if tipo else None,
        ))
    return result


async def get_by_id(session: AsyncSession, template_id: int) -> TemplateRead:
    template = await template_repo.get_by_id(session, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template ID {template_id} não encontrado.")
    tipo = await template_repo.get_tipo_by_id(session, template.tipo_template_id)
    return TemplateRead(
        id=template.id,
        nome=template.nome,
        tipo_template_id=template.tipo_template_id,
        repo_github=template.repo_github,
        tipo_nome=tipo.nome if tipo else None,
    )


async def delete(session: AsyncSession, template_id: int) -> None:
    template = await template_repo.get_by_id(session, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template ID {template_id} não encontrado.")
    await template_repo.delete(session, template)
