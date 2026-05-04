"""
tests/integration/test_templates_api.py
Testes de integração do módulo Templates.
"""

import pytest

TEMPLATES_ENDPOINT = "/api/v1/templates"
TIPOS_ENDPOINT = "/api/v1/templates/tipos"


async def _create_tipos(client):
    """Helper: cria os tipos padrão via API (necessário antes de criar templates)."""
    # Em produção os tipos existem via seed; nos testes precisamos criá-los diretamente
    # via sessão — aqui usamos o sample_tipo_lander/offer via fixture se disponível.
    pass


@pytest.mark.asyncio
async def test_create_template_sucesso(client, sample_tipo_lander):
    """Happy path: template válido → 201."""
    payload = {
        "nome": "VSL CNN v1",
        "tipo_template_id": sample_tipo_lander.id,
        "repo_github": "lander/cnn",
    }
    response = await client.post(TEMPLATES_ENDPOINT, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "VSL CNN v1"
    assert data["tipo_template_id"] == sample_tipo_lander.id
    assert data["tipo_nome"] == "lander"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_templates_vazio(client):
    """Sem templates → 200 com []."""
    response = await client.get(TEMPLATES_ENDPOINT)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_template_nao_encontrado(client):
    """ID inexistente → 404."""
    response = await client.get(f"{TEMPLATES_ENDPOINT}/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_sucesso(client, sample_tipo_lander):
    """Cria e deleta template → 204."""
    payload = {
        "nome": "VSL Fox v1",
        "tipo_template_id": sample_tipo_lander.id,
        "repo_github": "lander/fox",
    }
    create_resp = await client.post(TEMPLATES_ENDPOINT, json=payload)
    assert create_resp.status_code == 201
    template_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"{TEMPLATES_ENDPOINT}/{template_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"{TEMPLATES_ENDPOINT}/{template_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_templates_filtro_tipo(client, sample_tipo_lander, sample_tipo_offer):
    """Filtro por tipo_template_id retorna apenas templates daquele tipo."""
    await client.post(TEMPLATES_ENDPOINT, json={
        "nome": "CNN", "tipo_template_id": sample_tipo_lander.id, "repo_github": "lander/cnn"
    })
    await client.post(TEMPLATES_ENDPOINT, json={
        "nome": "Padrão", "tipo_template_id": sample_tipo_offer.id, "repo_github": "offer_section/padrao"
    })

    resp = await client.get(TEMPLATES_ENDPOINT, params={"tipo_template_id": sample_tipo_lander.id})
    assert resp.status_code == 200
    data = resp.json()
    assert all(t["tipo_template_id"] == sample_tipo_lander.id for t in data)
    assert all(t["tipo_nome"] == "lander" for t in data)
