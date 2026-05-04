"""
RedTrack Service — Integração via httpx (async).

Responsabilidades:
1. Registrar Landers via POST /v2/landers
2. Criar Campanhas via POST /v2/campaigns
3. Polling de status de deploy (verificar URL final ativa)

Toda comunicação é assíncrona via httpx.AsyncClient para não bloquear o Event Loop.

A lógica de listicle é guiada pela coluna integra_redtrack_offer da PlataformaCheckout:
    - integra_redtrack_offer = True  → plataforma usa links diretos → listicle = True
    - integra_redtrack_offer = False → RedTrack roteia (ex: ClickBank) → listicle = False
"""

import asyncio
import logging
from typing import Optional

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_headers() -> dict:
    """Headers padrão para autenticação na API do RedTrack."""
    if not settings.redtrack_api_key:
        raise RuntimeError(
            "REDTRACK_API_KEY não configurada. Verifique o arquivo .env."
        )
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Api-Key": settings.redtrack_api_key,
    }


async def register_lander(
    name: str,
    url: str,
    tracking_domain: str,
    listicle: bool,
) -> str:
    """
    Registra uma Lander no RedTrack via POST /v2/landers.

    A lógica de listicle é determinada pela plataforma de checkout:
    - integra_redtrack_offer=True (ex: genéricas) → listicle=True
    - integra_redtrack_offer=False (ex: ClickBank) → listicle=False

    Args:
        name: Nome formatado da lander
        url: URL pública da landing page (após deploy no GitHub Pages)
        tracking_domain: Domínio de rastreamento (ex: weightlossnow.com)
        listicle: True se usar links diretos, False se RedTrack roteia

    Returns:
        ID da lander criada no RedTrack (string)

    Raises:
        httpx.HTTPStatusError: Em caso de erro na API
        RuntimeError: Se a API não retornar o ID esperado
    """
    payload = {
        "name": name,
        "url": url,
        "tracking_domain": tracking_domain,
        "listicle": listicle,
    }

    logger.info(f"Registrando lander no RedTrack: '{name}' | URL: {url} | listicle={listicle}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.redtrack_api_url}/v2/landers",
            json=payload,
            headers=_get_headers(),
        )
        response.raise_for_status()

    data = response.json()

    # RedTrack retorna o ID no campo 'id' ou dentro de 'data.id'
    lander_id = data.get("id") or data.get("data", {}).get("id")
    if not lander_id:
        raise RuntimeError(
            f"RedTrack não retornou um ID de lander válido. Resposta: {data}"
        )

    logger.info(f"✅ Lander registrada no RedTrack: ID={lander_id}")
    return str(lander_id)


async def create_campaign(
    nome: str,
    lander_id: str,
    traffic_channel_id: str,
    tracking_domain: str,
    postback_url: Optional[str] = None,
    prelander_id: Optional[str] = None,
) -> dict:
    """
    Cria uma Campanha no RedTrack via POST /v2/campaigns.

    Args:
        nome: Nome da campanha
        lander_id: ID da lander no RedTrack
        traffic_channel_id: ID do traffic channel no RedTrack
        tracking_domain: Domínio de rastreamento
        postback_url: URL de postback S2S (opcional)
        prelander_id: ID da pre-lander no RedTrack (opcional)

    Returns:
        Dict com 'campaign_id' e 'url_cloaker'
    """
    payload: dict = {
        "name": nome,
        "lander_id": lander_id,
        "traffic_channel_id": traffic_channel_id,
        "domain": tracking_domain,
    }

    if postback_url:
        payload["postback_url"] = postback_url
    if prelander_id:
        payload["prelander_id"] = prelander_id

    logger.info(f"Criando campanha no RedTrack: '{nome}'")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.redtrack_api_url}/v2/campaigns",
            json=payload,
            headers=_get_headers(),
        )
        response.raise_for_status()

    data = response.json()
    campaign_id = str(data.get("id") or data.get("data", {}).get("id", ""))
    url_cloaker = data.get("url") or data.get("data", {}).get("url", "")

    logger.info(f"✅ Campanha criada: ID={campaign_id} | URL: {url_cloaker}")

    return {
        "campaign_id": campaign_id,
        "url_cloaker": url_cloaker,
    }


async def get_or_create_traffic_channel(nome: str) -> str:
    """
    Busca ou cria um Traffic Channel no RedTrack.
    Implementa a função 'getOrCreateTrafficChannel' do fluxo documentado.

    Args:
        nome: Nome do canal de tráfego (ex: 'Taboola', 'Outbrain')

    Returns:
        ID do traffic channel no RedTrack
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Busca canais existentes
        response = await client.get(
            f"{settings.redtrack_api_url}/v2/traffic-channels",
            headers=_get_headers(),
        )
        response.raise_for_status()

    channels = response.json().get("data", response.json())
    if isinstance(channels, list):
        for channel in channels:
            if channel.get("name", "").lower() == nome.lower():
                logger.info(f"Traffic Channel encontrado: '{nome}' (ID: {channel['id']})")
                return str(channel["id"])

    # Não encontrou — cria um novo
    logger.info(f"Traffic Channel '{nome}' não encontrado. Criando...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.redtrack_api_url}/v2/traffic-channels",
            json={"name": nome},
            headers=_get_headers(),
        )
        response.raise_for_status()

    new_channel = response.json()
    channel_id = str(new_channel.get("id") or new_channel.get("data", {}).get("id"))
    logger.info(f"✅ Traffic Channel criado: '{nome}' (ID: {channel_id})")
    return channel_id


async def poll_url_until_live(
    url: str,
    timeout_seconds: int = 300,
    interval_seconds: int = 15,
) -> bool:
    """
    Faz polling HTTP na URL da lander até receber Status 200 ou atingir o timeout.
    Necessário porque o GitHub Pages pode demorar para propagar após o commit.

    Args:
        url: URL pública da landing page
        timeout_seconds: Tempo máximo de espera (default: 300s = 5min)
        interval_seconds: Intervalo entre tentativas (default: 15s)

    Returns:
        True se a URL retornou 200 dentro do timeout, False caso contrário
    """
    elapsed = 0
    logger.info(f"Iniciando polling para: {url} (timeout: {timeout_seconds}s)")

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        while elapsed < timeout_seconds:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"✅ URL ativa: {url} (após {elapsed}s)")
                    return True
                logger.info(f"Status {response.status_code} em {url}. Aguardando {interval_seconds}s...")
            except httpx.RequestError as e:
                logger.warning(f"Erro de conexão ({elapsed}s): {e}")

            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds

    logger.error(f"❌ Timeout de {timeout_seconds}s atingido para: {url}")
    return False
