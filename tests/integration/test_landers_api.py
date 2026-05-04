"""
tests/integration/test_landers_api.py

Testes de integração do módulo Landers.
Chamam a API via AsyncClient com banco in-memory e GitHub mockado.
"""

import pytest

from backend.models.dominio import Dominio
from backend.models.plataforma import Nicho, PlataformaCheckout
from backend.models.produto import Produto
from backend.models.template import Template

COMPILE_ENDPOINT = "/api/v1/landers/compile"


def _payload(
    produto: Produto,
    nicho: Nicho,
    dominio: Dominio,
    template_index: Template,
    template_offer: Template,
    **overrides,
) -> dict:
    """Monta payload válido de compilação a partir das fixtures de banco."""
    base = {
        "produto_id": produto.id,
        "template_index_id": template_index.id,
        "template_offer_id": template_offer.id,
        "nome_produto": "Gelatide",
        "headline": "Perca 10kg em 30 dias",
        "vturb_preload": "",
        "vturb_script": "<script>embed</script>",
        "vturb_delay": "12:30",
        "nicho_id": nicho.id,
        "dominio_id": dominio.id,
    }
    return {**base, **overrides}


# =============================================================================
# POST /landers/compile
# =============================================================================

@pytest.mark.asyncio
async def test_compile_lander_sucesso(
    client, mock_github,
    sample_produto, sample_nicho, sample_dominio,
    sample_template_index, sample_template_offer,
):
    """Happy path: payload válido → 201 com lander_id e delay correto."""
    payload = _payload(
        sample_produto, sample_nicho, sample_dominio,
        sample_template_index, sample_template_offer,
    )
    response = await client.post(COMPILE_ENDPOINT, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "lander_id" in data
    assert data["vturb_delay_segundos"] == 750  # 12*60 + 30
    assert "<html>" in data["html_index_preview"]
    assert "<html>" in data["html_offer_preview"]


@pytest.mark.asyncio
async def test_compile_lander_delay_invalido(client):
    """Delay em formato errado → 422 Unprocessable Entity."""
    payload = {
        "produto_id": 1, "template_index_id": 1, "template_offer_id": 2,
        "nome_produto": "X",
        "headline": "H", "vturb_delay": "1230",
        "nicho_id": 1, "dominio_id": 1,
    }
    response = await client.post(COMPILE_ENDPOINT, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compile_lander_delay_segundos_invalidos(client):
    """Segundos >= 60 → 422 Unprocessable Entity."""
    payload = {
        "produto_id": 1, "template_index_id": 1, "template_offer_id": 2,
        "nome_produto": "X",
        "headline": "H", "vturb_delay": "12:60",
        "nicho_id": 1, "dominio_id": 1,
    }
    response = await client.post(COMPILE_ENDPOINT, json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compile_lander_produto_nao_encontrado(
    client, mock_github,
    sample_nicho, sample_dominio,
    sample_template_index, sample_template_offer,
):
    """produto_id inexistente → 404."""
    payload = {
        "produto_id": 9999,
        "template_index_id": sample_template_index.id,
        "template_offer_id": sample_template_offer.id,
        "nome_produto": "X",
        "headline": "H", "vturb_delay": "12:30",
        "nicho_id": sample_nicho.id,
        "dominio_id": sample_dominio.id,
    }
    response = await client.post(COMPILE_ENDPOINT, json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_compile_lander_nicho_nao_encontrado(
    client, mock_github,
    sample_produto, sample_dominio,
    sample_template_index, sample_template_offer,
):
    """nicho_id inexistente → 404."""
    payload = _payload(
        sample_produto, sample_produto, sample_dominio,  # nicho embutido no produto
        sample_template_index, sample_template_offer,
        nicho_id=9999,
    )
    response = await client.post(COMPILE_ENDPOINT, json=payload)
    assert response.status_code == 404


# =============================================================================
# GET /landers
# =============================================================================

@pytest.mark.asyncio
async def test_list_landers_banco_vazio(client):
    """Sem nenhuma lander cadastrada → 200 com lista vazia."""
    response = await client.get("/api/v1/landers")
    assert response.status_code == 200
    assert response.json() == []


# =============================================================================
# GET /landers/{id}
# =============================================================================

@pytest.mark.asyncio
async def test_get_lander_status_nao_encontrada(client):
    """ID inexistente → 404."""
    response = await client.get("/api/v1/landers/9999")
    assert response.status_code == 404


# =============================================================================
# POST /landers/deploy/{id}
# =============================================================================

@pytest.mark.asyncio
async def test_deploy_lander_ja_deployada(client, sample_lander_deployed):
    """Lander com url_final já definida → 409 Conflict."""
    response = await client.post(f"/api/v1/landers/deploy/{sample_lander_deployed.id}", json={})
    assert response.status_code == 409
    assert "já foi deployada" in response.json()["detail"]
