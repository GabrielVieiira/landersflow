"""
Schemas Pydantic: Template e TipoTemplate
"""

from pydantic import BaseModel


class TipoTemplateRead(BaseModel):
    id: int
    nome: str


class TemplateCreate(BaseModel):
    nome: str
    tipo_template_id: int
    repo_github: str


class TemplateRead(BaseModel):
    id: int
    nome: str
    tipo_template_id: int
    repo_github: str
    tipo_nome: str | None = None  # nome do tipo (ex: 'lander', 'offer_section')
