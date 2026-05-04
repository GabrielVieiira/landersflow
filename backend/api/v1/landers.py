"""
Router: Landers (api/v1)
Handlers HTTP finos — apenas recebem request, chamam o service e retornam response.
Nenhuma lógica de negócio ou query SQL aqui.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.schemas.lander import (
    CompileLanderRequest,
    CompileLanderResponse,
    DeployStatusResponse,
    LanderListItem,
)
from backend.services import lander_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landers", tags=["Landers"])


@router.post(
    "/compile",
    response_model=CompileLanderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compilar Lander",
)
async def compile_lander(
    payload: CompileLanderRequest,
    session: AsyncSession = Depends(get_session),
) -> CompileLanderResponse:
    """Compila templates via Jinja2 e retorna preview HTML para QA. Não faz deploy."""
    return await lander_service.compile(session, payload)


@router.post(
    "/deploy/{lander_id}",
    response_model=DeployStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Deploy de Lander",
)
async def deploy_lander(
    lander_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> DeployStatusResponse:
    """Inicia deploy no GitHub Pages em background. Retorna 202 imediatamente."""
    return await lander_service.deploy(session, lander_id, background_tasks)


@router.get(
    "",
    response_model=list[LanderListItem],
    summary="Listar Landers",
)
async def list_landers(
    session: AsyncSession = Depends(get_session),
) -> list[LanderListItem]:
    """Retorna todas as landers com status resumido."""
    return await lander_service.list_landers(session)


@router.get(
    "/{lander_id}",
    response_model=DeployStatusResponse,
    summary="Status de uma Lander",
)
async def get_lander_status(
    lander_id: int,
    session: AsyncSession = Depends(get_session),
) -> DeployStatusResponse:
    """Retorna o status de deploy de uma lander específica."""
    return await lander_service.get_status(session, lander_id)
