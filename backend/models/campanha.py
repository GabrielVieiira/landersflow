"""
Modelo: Campanha
"""

from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.lander import Lander
    from backend.models.traffic import TrafficChannel


class Campanha(SQLModel, table=True):
    __tablename__ = "campanha"

    id: Optional[int] = Field(default=None, primary_key=True)
    lander_id: int = Field(foreign_key="lander.id", nullable=False)
    traffic_channel_id: int = Field(foreign_key="traffic_channel.id", nullable=False)
    nome: str = Field(max_length=200, nullable=False)
    redtrack_campaign_id: Optional[str] = Field(default=None, max_length=100)
    url_cloaker: Optional[str] = Field(default=None, max_length=500)

    # Relacionamentos
    lander: Optional["Lander"] = Relationship(back_populates="campanhas")
    traffic_channel: Optional["TrafficChannel"] = Relationship(back_populates="campanhas")
