"""
Schemas Pydantic: Produto
Extraídos de backend/routes/produtos.py
"""

from typing import List, Optional

from pydantic import BaseModel


class ProdutoVariacaoCreate(BaseModel):
    quantidade_potes: int
    checkout_identifier: str
    url_imagem: str


class ProdutoCheckoutParamCreate(BaseModel):
    chave: str
    valor: str


class ProdutoCreate(BaseModel):
    nicho_id: int
    plataforma_checkout_id: int
    nome: str
    cor_primaria: str
    cor_secundaria: str
    cor_background: str
    variacoes: List[ProdutoVariacaoCreate] = []
    checkout_params: List[ProdutoCheckoutParamCreate] = []


class ProdutoRead(BaseModel):
    id: int
    nome: str
    nicho_id: int
    plataforma_checkout_id: int
    cor_primaria: str
    cor_secundaria: str
    cor_background: str
    variacoes: List[ProdutoVariacaoCreate] = []
