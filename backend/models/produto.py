"""
Modelos: Produto, ProdutoVariacao, ProdutoCheckoutParam
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.lander import Lander
    from backend.models.plataforma import Nicho, PlataformaCheckout


class Produto(SQLModel, table=True):
    __tablename__ = "produto"

    id: Optional[int] = Field(default=None, primary_key=True)
    nicho_id: int = Field(foreign_key="nicho.id", nullable=False)
    plataforma_checkout_id: int = Field(foreign_key="plataforma_checkout.id", nullable=False)
    nome: str = Field(max_length=200, nullable=False)
    cor_primaria: str = Field(max_length=7, nullable=False)
    cor_secundaria: str = Field(max_length=7, nullable=False)
    cor_background: str = Field(max_length=7, nullable=False)

    # Relacionamentos
    nicho: Optional["Nicho"] = Relationship(back_populates="produtos")
    plataforma_checkout: Optional["PlataformaCheckout"] = Relationship(back_populates="produtos")
    variacoes: List["ProdutoVariacao"] = Relationship(back_populates="produto")
    checkout_params: List["ProdutoCheckoutParam"] = Relationship(back_populates="produto")
    landers: List["Lander"] = Relationship(back_populates="produto")


class ProdutoVariacao(SQLModel, table=True):
    __tablename__ = "produto_variacao"

    id: Optional[int] = Field(default=None, primary_key=True)
    produto_id: int = Field(foreign_key="produto.id", nullable=False)
    quantidade_potes: int = Field(nullable=False)
    checkout_identifier: str = Field(max_length=500, nullable=False)
    url_imagem: str = Field(max_length=500, nullable=False)

    # Relacionamentos
    produto: Optional["Produto"] = Relationship(back_populates="variacoes")


class ProdutoCheckoutParam(SQLModel, table=True):
    __tablename__ = "produto_checkout_param"

    id: Optional[int] = Field(default=None, primary_key=True)
    produto_id: int = Field(foreign_key="produto.id", nullable=False)
    chave: str = Field(max_length=100, nullable=False)
    valor: str = Field(max_length=500, nullable=False)

    # Relacionamentos
    produto: Optional["Produto"] = Relationship(back_populates="checkout_params")
