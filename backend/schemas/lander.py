"""
Schemas Pydantic: Lander
Contratos de request/response da camada HTTP para o módulo de Landers.
"""

import re
from typing import Optional

from pydantic import BaseModel, field_validator

# Regex local para evitar import circular com services.compiler
_DELAY_PATTERN = re.compile(r"^\d{1,2}:\d{2}$")


class CompileLanderRequest(BaseModel):
    """
    Payload de entrada para compilação de Lander.
    Segue o contrato de dados definido na Documentação Técnica §1.
    """

    produto_id: int
    template_index_id: int
    template_offer_id: int
    nome_produto: str
    headline: str
    vturb_preload: str = ""
    vturb_script: str = ""
    vturb_delay: str  # Formato "MM:SS" (ex: "12:30")
    nicho_id: int
    dominio_id: int

    @field_validator("vturb_delay")
    @classmethod
    def validate_vturb_delay(cls, v: str) -> str:
        if not _DELAY_PATTERN.match(v):
            raise ValueError(f"Formato de delay inválido: '{v}'. Esperado: 'MM:SS' (ex: '12:30')")
        parts = v.split(":")
        if int(parts[1]) >= 60:
            raise ValueError(f"Segundos inválidos: {parts[1]}. Deve ser entre 0 e 59.")
        return v


class CompileLanderResponse(BaseModel):
    """Resposta com os HTMLs compilados para revisão visual (QA)."""

    lander_id: int
    vturb_delay_segundos: int
    html_index_preview: str
    html_offer_preview: str
    message: str = "Lander compilada com sucesso. Revise e acione o deploy."


class DeployStatusResponse(BaseModel):
    """Status do deploy de uma lander."""

    lander_id: int
    url_final: Optional[str]
    redtrack_lander_id: Optional[str]
    status: str  # "pending" | "deploying" | "live" | "error"
    message: str


class LanderListItem(BaseModel):
    """Item resumido para listagem de landers."""

    id: int
    produto_nome: str
    headline: str
    url_final: Optional[str]
    redtrack_lander_id: Optional[str]
    vturb_delay_segundos: int
