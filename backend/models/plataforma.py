"""
Modelos: Nicho e PlataformaCheckout
Núcleo de negócio — define o ambiente e a engine de pagamento de cada produto.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.dominio import Dominio
    from backend.models.produto import Produto


class Nicho(SQLModel, table=True):
    __tablename__ = "nicho"

    id: Optional[int] = Field(default=None, primary_key=True)
    sigla: str = Field(max_length=10, unique=True, nullable=False)
    nome: str = Field(max_length=100, nullable=False)

    # Relacionamentos
    produtos: List["Produto"] = Relationship(back_populates="nicho")
    dominios: List["Dominio"] = Relationship(back_populates="nicho")


class PlataformaCheckout(SQLModel, table=True):
    __tablename__ = "plataforma_checkout"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100, nullable=False)
    slug_aplicacao: str = Field(max_length=50, unique=True, nullable=False)
    integra_redtrack_offer: bool = Field(default=False, nullable=False)
    padrao_link_html: str = Field(
        max_length=500,
        nullable=False,
        description=(
            "Template de atributos do botão. Suporta {url} e {qtd}. "
            "Ex: 'href=\"{url}\"'"
        ),
    )

    # Relacionamentos
    produtos: List["Produto"] = Relationship(back_populates="plataforma_checkout")
