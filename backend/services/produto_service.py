"""
Service: Produto
CRUD de Produtos com validação de FK (nicho, plataforma).
"""

import logging
from typing import Optional

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.repositories import produto_repo
from backend.schemas.produto import ProdutoCreate, ProdutoRead, ProdutoVariacaoCreate

logger = logging.getLogger(__name__)


async def create(session: AsyncSession, payload: ProdutoCreate) -> ProdutoRead:
    """Cria produto com variações e parâmetros de checkout."""
    nicho = await produto_repo.get_nicho_by_id(session, payload.nicho_id)
    if not nicho:
        raise HTTPException(status_code=404, detail=f"Nicho ID {payload.nicho_id} não encontrado.")

    plataforma = await produto_repo.get_plataforma_by_id(session, payload.plataforma_checkout_id)
    if not plataforma:
        raise HTTPException(
            status_code=404,
            detail=f"PlataformaCheckout ID {payload.plataforma_checkout_id} não encontrada.",
        )

    produto = await produto_repo.create(
        session,
        nicho_id=payload.nicho_id,
        plataforma_checkout_id=payload.plataforma_checkout_id,
        nome=payload.nome,
        cor_primaria=payload.cor_primaria,
        cor_secundaria=payload.cor_secundaria,
        cor_background=payload.cor_background,
    )

    variacoes_read = []
    for v in payload.variacoes:
        await produto_repo.add_variacao(
            session,
            produto_id=produto.id,
            quantidade_potes=v.quantidade_potes,
            checkout_identifier=v.checkout_identifier,
            url_imagem=v.url_imagem,
        )
        variacoes_read.append(ProdutoVariacaoCreate(**v.model_dump()))

    for p in payload.checkout_params:
        await produto_repo.add_checkout_param(
            session, produto_id=produto.id, chave=p.chave, valor=p.valor
        )

    logger.info(f"Produto criado: '{produto.nome}' (ID: {produto.id})")

    return ProdutoRead(
        id=produto.id,
        nome=produto.nome,
        nicho_id=produto.nicho_id,
        plataforma_checkout_id=produto.plataforma_checkout_id,
        cor_primaria=produto.cor_primaria,
        cor_secundaria=produto.cor_secundaria,
        cor_background=produto.cor_background,
        variacoes=variacoes_read,
    )


async def list_all(
    session: AsyncSession, nicho_id: Optional[int] = None
) -> list[ProdutoRead]:
    """Lista todos os produtos com suas variações."""
    produtos = await produto_repo.list_all(session, nicho_id=nicho_id)
    result = []
    for p in produtos:
        variacoes = await produto_repo.get_variacoes(session, p.id)
        result.append(
            ProdutoRead(
                id=p.id,
                nome=p.nome,
                nicho_id=p.nicho_id,
                plataforma_checkout_id=p.plataforma_checkout_id,
                cor_primaria=p.cor_primaria,
                cor_secundaria=p.cor_secundaria,
                cor_background=p.cor_background,
                variacoes=[
                    ProdutoVariacaoCreate(
                        quantidade_potes=v.quantidade_potes,
                        checkout_identifier=v.checkout_identifier,
                        url_imagem=v.url_imagem,
                    )
                    for v in variacoes.values()
                ],
            )
        )
    return result


async def get_by_id(session: AsyncSession, produto_id: int) -> ProdutoRead:
    """Retorna um produto com suas variações."""
    produto = await produto_repo.get_by_id(session, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail=f"Produto ID {produto_id} não encontrado.")

    variacoes = await produto_repo.get_variacoes(session, produto_id)

    return ProdutoRead(
        id=produto.id,
        nome=produto.nome,
        nicho_id=produto.nicho_id,
        plataforma_checkout_id=produto.plataforma_checkout_id,
        cor_primaria=produto.cor_primaria,
        cor_secundaria=produto.cor_secundaria,
        cor_background=produto.cor_background,
        variacoes=[
            ProdutoVariacaoCreate(
                quantidade_potes=v.quantidade_potes,
                checkout_identifier=v.checkout_identifier,
                url_imagem=v.url_imagem,
            )
            for v in variacoes.values()
        ],
    )
