"""
Repository: Produto, Nicho, PlataformaCheckout, Domínio, ProdutoVariacao
Única camada que executa queries SQL nessas tabelas.
Os services nunca chamam session.exec() diretamente — sempre passam por aqui.
"""

from typing import Optional

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.dominio import Dominio
from backend.models.plataforma import Nicho, PlataformaCheckout
from backend.models.produto import Produto, ProdutoCheckoutParam, ProdutoVariacao


async def get_nicho_by_id(session: AsyncSession, nicho_id: int) -> Optional[Nicho]:
    return await session.get(Nicho, nicho_id)


async def get_plataforma_by_id(
    session: AsyncSession, plataforma_id: int
) -> Optional[PlataformaCheckout]:
    return await session.get(PlataformaCheckout, plataforma_id)


async def get_dominio_by_id(session: AsyncSession, dominio_id: int) -> Optional[Dominio]:
    return await session.get(Dominio, dominio_id)


async def get_by_id(session: AsyncSession, produto_id: int) -> Optional[Produto]:
    return await session.get(Produto, produto_id)


async def get_variacoes(
    session: AsyncSession, produto_id: int
) -> dict[int, ProdutoVariacao]:
    result = await session.exec(
        select(ProdutoVariacao).where(ProdutoVariacao.produto_id == produto_id)
    )
    return {v.quantidade_potes: v for v in result.all()}


async def get_with_relations(
    session: AsyncSession, produto_id: int
) -> tuple[Produto, PlataformaCheckout, dict[int, ProdutoVariacao]]:
    """
    Carrega produto + plataforma + variações de uma só vez.
    Lança HTTPException 404/500 se alguma entidade não existir.
    Chamado pelos services — nunca pelos handlers HTTP.
    """
    produto = await get_by_id(session, produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail=f"Produto ID {produto_id} não encontrado.")

    plataforma = await get_plataforma_by_id(session, produto.plataforma_checkout_id)
    if not plataforma:
        raise HTTPException(
            status_code=500,
            detail=f"PlataformaCheckout ID {produto.plataforma_checkout_id} não encontrada.",
        )

    variacoes = await get_variacoes(session, produto_id)
    return produto, plataforma, variacoes


async def list_all(
    session: AsyncSession, nicho_id: Optional[int] = None
) -> list[Produto]:
    query = select(Produto)
    if nicho_id:
        query = query.where(Produto.nicho_id == nicho_id)
    result = await session.exec(query)
    return list(result.all())


async def create(
    session: AsyncSession,
    nicho_id: int,
    plataforma_checkout_id: int,
    nome: str,
    cor_primaria: str,
    cor_secundaria: str,
    cor_background: str,
) -> Produto:
    produto = Produto(
        nicho_id=nicho_id,
        plataforma_checkout_id=plataforma_checkout_id,
        nome=nome,
        cor_primaria=cor_primaria,
        cor_secundaria=cor_secundaria,
        cor_background=cor_background,
    )
    session.add(produto)
    await session.flush()
    return produto


async def add_variacao(
    session: AsyncSession,
    produto_id: int,
    quantidade_potes: int,
    checkout_identifier: str,
    url_imagem: str,
) -> ProdutoVariacao:
    v = ProdutoVariacao(
        produto_id=produto_id,
        quantidade_potes=quantidade_potes,
        checkout_identifier=checkout_identifier,
        url_imagem=url_imagem,
    )
    session.add(v)
    await session.flush()
    return v


async def add_checkout_param(
    session: AsyncSession, produto_id: int, chave: str, valor: str
) -> ProdutoCheckoutParam:
    p = ProdutoCheckoutParam(produto_id=produto_id, chave=chave, valor=valor)
    session.add(p)
    await session.flush()
    return p
