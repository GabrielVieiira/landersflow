"""
Router: Campanhas (api/v1)
Handlers HTTP finos — chamam campanha_service e retornam response.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.schemas.campanha import CampanhaCreate, CampanhaRead
from backend.services import campanha_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


@router.post("", response_model=CampanhaRead, status_code=status.HTTP_201_CREATED)
async def create_campanha(
    payload: CampanhaCreate,
    session: AsyncSession = Depends(get_session),
) -> CampanhaRead:
    """Cria campanha completa no RedTrack e persiste localmente."""
    return await campanha_service.create(session, payload)


@router.get("", response_model=List[CampanhaRead])
async def list_campanhas(
    session: AsyncSession = Depends(get_session),
) -> List[CampanhaRead]:
    """Lista todas as campanhas."""
    return await campanha_service.list_all(session)
