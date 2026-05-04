"""
Schemas Pydantic: Campanha
Extraídos de backend/routes/campanhas.py
"""

from typing import Optional

from pydantic import BaseModel


class CampanhaCreate(BaseModel):
    """
    Payload de criação de campanha.
    Segue o fluxo documentado (§10 do fluxo de automação):
        1. Nome da Campanha
        2. Nome do Traffic Channel (criado automaticamente se não existir)
        3. ID da Lander no sistema
        4. Postback URL S2S (opcional)
        5. Pre-lander ID no RedTrack (opcional)
    """
    nome: str
    traffic_channel_nome: str
    lander_id: int
    postback_url: Optional[str] = None
    prelander_redtrack_id: Optional[str] = None


class CampanhaRead(BaseModel):
    id: int
    nome: str
    lander_id: int
    traffic_channel_id: int
    redtrack_campaign_id: Optional[str]
    url_cloaker: Optional[str]
