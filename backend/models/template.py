"""
Modelos: TipoTemplate e Template.

TipoTemplate é uma tabela de lookup normalizada (substitui o enum antigo).
Valores iniciais (via seed): 1=lander, 2=offer_section
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.lander import Lander


class TipoTemplate(SQLModel, table=True):
    """Tabela de lookup para os tipos de template (lander, offer_section)."""
    __tablename__ = "tipo_template"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100, unique=True, nullable=False)

    templates: List["Template"] = Relationship(back_populates="tipo")


class Template(SQLModel, table=True):
    __tablename__ = "template"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=200, nullable=False)
    tipo_template_id: int = Field(foreign_key="tipo_template.id", nullable=False)
    repo_github: str = Field(max_length=500, nullable=False)

    # Relacionamentos
    tipo: Optional[TipoTemplate] = Relationship(back_populates="templates")

    landers_como_index: List["Lander"] = Relationship(
        back_populates="template_index",
        sa_relationship_kwargs={"foreign_keys": "[Lander.template_index_id]"},
    )
    landers_como_offer: List["Lander"] = Relationship(
        back_populates="template_offer",
        sa_relationship_kwargs={"foreign_keys": "[Lander.template_offer_id]"},
    )
