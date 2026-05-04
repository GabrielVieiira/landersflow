"""
Modelos: TrafficChannel e TrafficChannelPostback
"""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from backend.models.campanha import Campanha


class TrafficChannel(SQLModel, table=True):
    __tablename__ = "traffic_channel"

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100, unique=True, nullable=False)
    identificador_api: str = Field(max_length=100, nullable=False)

    # Relacionamentos
    postbacks: List["TrafficChannelPostback"] = Relationship(back_populates="traffic_channel")
    campanhas: List["Campanha"] = Relationship(back_populates="traffic_channel")


class TrafficChannelPostback(SQLModel, table=True):
    __tablename__ = "traffic_channel_postback"

    id: Optional[int] = Field(default=None, primary_key=True)
    traffic_channel_id: int = Field(foreign_key="traffic_channel.id", nullable=False)
    evento: str = Field(max_length=50, nullable=False)
    url_postback: str = Field(max_length=500, nullable=False)

    # Relacionamentos
    traffic_channel: Optional["TrafficChannel"] = Relationship(back_populates="postbacks")
