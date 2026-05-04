"""
Modelo: Lander
Entidade central do sistema. Representa uma landing page compilada.
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.campanha import Campanha
    from backend.models.dominio import Dominio
    from backend.models.produto import Produto
    from backend.models.template import Template


class Lander(SQLModel, table=True):
    __tablename__ = "lander"

    id: Optional[int] = Field(default=None, primary_key=True)
    produto_id: int = Field(foreign_key="produto.id", nullable=False)
    template_index_id: int = Field(foreign_key="template.id", nullable=False)
    template_offer_id: int = Field(foreign_key="template.id", nullable=False)
    dominio_id: int = Field(foreign_key="dominio.id", nullable=False)
    headline: str = Field(max_length=500, nullable=False)
    vturb_preload: str = Field(default="")
    vturb_script: str = Field(default="")
    vturb_delay_segundos: int = Field(nullable=False)
    redtrack_lander_id: Optional[str] = Field(default=None, max_length=100)
    url_final: Optional[str] = Field(default=None, max_length=500)

    # Relacionamentos
    produto: Optional["Produto"] = Relationship(back_populates="landers")
    template_index: Optional["Template"] = Relationship(
        back_populates="landers_como_index",
        sa_relationship_kwargs={"foreign_keys": "[Lander.template_index_id]"},
    )
    template_offer: Optional["Template"] = Relationship(
        back_populates="landers_como_offer",
        sa_relationship_kwargs={"foreign_keys": "[Lander.template_offer_id]"},
    )
    dominio: Optional["Dominio"] = Relationship(back_populates="landers")
    campanhas: List["Campanha"] = Relationship(back_populates="lander")
