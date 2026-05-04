"""
Router: Produtos (api/v1)
Handlers HTTP finos — chamam produto_service e retornam response.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.schemas.produto import ProdutoCreate, ProdutoRead
from backend.services import produto_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.post("", response_model=ProdutoRead, status_code=status.HTTP_201_CREATED)
async def create_produto(
    payload: ProdutoCreate,
    session: AsyncSession = Depends(get_session),
) -> ProdutoRead:
    """Cadastra um novo produto com suas variações e parâmetros de checkout."""
    return await produto_service.create(session, payload)


@router.get("", response_model=List[ProdutoRead])
async def list_produtos(
    nicho_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
) -> List[ProdutoRead]:
    """Lista todos os produtos, com filtro opcional por nicho."""
    return await produto_service.list_all(session, nicho_id=nicho_id)


@router.get("/{produto_id}", response_model=ProdutoRead)
async def get_produto(
    produto_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProdutoRead:
    """Retorna detalhes de um produto específico."""
    return await produto_service.get_by_id(session, produto_id)
