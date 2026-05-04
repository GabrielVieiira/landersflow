"""
Router: Templates (api/v1)
Handlers HTTP finos — chamam template_service e retornam response.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.schemas.template import TemplateCreate, TemplateRead, TipoTemplateRead
from backend.services import template_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/tipos", response_model=List[TipoTemplateRead])
async def list_tipos(
    session: AsyncSession = Depends(get_session),
) -> List[TipoTemplateRead]:
    """Lista todos os tipos de template disponíveis (lander, offer_section)."""
    return await template_service.list_tipos(session)


@router.post("", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    session: AsyncSession = Depends(get_session),
) -> TemplateRead:
    """Cadastra um novo template HTML."""
    return await template_service.create(session, payload)


@router.get("", response_model=List[TemplateRead])
async def list_templates(
    tipo_template_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
) -> List[TemplateRead]:
    """Lista templates com filtro opcional por tipo_template_id."""
    return await template_service.list_all(session, tipo_template_id=tipo_template_id)


@router.get("/{template_id}", response_model=TemplateRead)
async def get_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> TemplateRead:
    """Retorna um template específico."""
    return await template_service.get_by_id(session, template_id)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove um template do banco."""
    await template_service.delete(session, template_id)
