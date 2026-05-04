"""
Cloudflare Service — Integração via httpx (async).

Responsabilidades:
1. Verificar status de zonas DNS
2. Criar registros CNAME (para apontar para GitHub Pages)
3. Criar registros A (para apontar para servidores)
4. Consultar propagação DNS

Toda comunicação é assíncrona via httpx.AsyncClient.
"""

import logging
from typing import Optional

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"


def _get_headers() -> dict:
    """Headers de autenticação para a API do Cloudflare."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.secret_key}",
    }


async def get_zone_status(zone_id: str) -> dict:
    """
    Consulta o status de uma Zone DNS no Cloudflare.

    Args:
        zone_id: ID da zone no Cloudflare

    Returns:
        Dict com status e informações da zone
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}",
            headers=_get_headers(),
        )
        response.raise_for_status()

    data = response.json()
    zone = data.get("result", {})
    logger.info(f"Zone status: {zone.get('name')} → {zone.get('status')}")
    return zone


async def create_cname_record(
    zone_id: str,
    name: str,
    target: str,
    proxied: bool = True,
) -> dict:
    """
    Cria um registro CNAME no Cloudflare (ex: www → owner.github.io).

    Args:
        zone_id: ID da zone no Cloudflare
        name: Nome do registro (ex: 'www' ou '@')
        target: Destino do CNAME (ex: 'owner.github.io')
        proxied: Se True, ativa o proxy Cloudflare (nuvem laranja)

    Returns:
        Dict com dados do registro criado
    """
    payload = {
        "type": "CNAME",
        "name": name,
        "content": target,
        "proxied": proxied,
        "ttl": 1,  # Auto TTL quando proxied=True
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
            json=payload,
            headers=_get_headers(),
        )
        response.raise_for_status()

    result = response.json().get("result", {})
    logger.info(f"✅ CNAME criado: {name} → {target} (proxied={proxied})")
    return result


async def create_a_record(
    zone_id: str,
    name: str,
    ip_address: str,
    proxied: bool = True,
) -> dict:
    """
    Cria um registro A no Cloudflare (aponta para IP do servidor).

    GitHub Pages IPs: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153

    Args:
        zone_id: ID da zone no Cloudflare
        name: Nome do registro (ex: '@' para raiz)
        ip_address: Endereço IP de destino
        proxied: Se True, ativa o proxy Cloudflare

    Returns:
        Dict com dados do registro criado
    """
    payload = {
        "type": "A",
        "name": name,
        "content": ip_address,
        "proxied": proxied,
        "ttl": 1,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{CLOUDFLARE_API_BASE}/zones/{zone_id}/dns_records",
            json=payload,
            headers=_get_headers(),
        )
        response.raise_for_status()

    result = response.json().get("result", {})
    logger.info(f"✅ Registro A criado: {name} → {ip_address}")
    return result


async def setup_github_pages_dns(
    zone_id: str,
    github_pages_username: str,
) -> list[dict]:
    """
    Configura os registros DNS necessários para apontar um domínio para o GitHub Pages.
    Segue o padrão documentado no fluxo de automação.

    IPs oficiais do GitHub Pages (2024):
        185.199.108.153
        185.199.109.153
        185.199.110.153
        185.199.111.153

    Args:
        zone_id: ID da zone no Cloudflare
        github_pages_username: Username/org do GitHub (ex: 'minha-org')

    Returns:
        Lista de registros criados
    """
    github_pages_ips = [
        "185.199.108.153",
        "185.199.109.153",
        "185.199.110.153",
        "185.199.111.153",
    ]

    created_records = []

    # Cria registros A para os 4 IPs do GitHub Pages
    for ip in github_pages_ips:
        record = await create_a_record(zone_id, "@", ip, proxied=True)
        created_records.append(record)

    # Cria CNAME para www apontando para github.io
    cname_target = f"{github_pages_username}.github.io"
    cname_record = await create_cname_record(zone_id, "www", cname_target, proxied=True)
    created_records.append(cname_record)

    logger.info(f"✅ DNS do GitHub Pages configurado para zone: {zone_id}")
    return created_records
