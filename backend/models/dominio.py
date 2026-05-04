"""
Modelo: Dominio
Gerencia os domínios de hospedagem atrelados a cada nicho.
"""

from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, String

if TYPE_CHECKING:
    from backend.models.lander import Lander
    from backend.models.plataforma import Nicho


class StatusDNS(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"


class Dominio(SQLModel, table=True):
    __tablename__ = "dominio"

    id: Optional[int] = Field(default=None, primary_key=True)
    nicho_id: int = Field(foreign_key="nicho.id", nullable=False)
    url: str = Field(max_length=255, nullable=False, unique=True)
    cloudflare_zone_id: str = Field(max_length=100, nullable=False)
    status_dns: StatusDNS = Field(
        default=StatusDNS.PENDING,
        # Usa String em vez do tipo Enum do SQLAlchemy para evitar o conflito
        # entre nomes dos membros (ACTIVE) e valores (active) na leitura do banco.
        # O Pydantic/SQLModel faz a coerção 'active' -> StatusDNS.ACTIVE automaticamente.
        sa_column=Column(String(20), nullable=False, default=StatusDNS.PENDING.value),
    )

    # Relacionamentos
    nicho: Optional["Nicho"] = Relationship(back_populates="dominios")
    landers: List["Lander"] = Relationship(back_populates="dominio")
