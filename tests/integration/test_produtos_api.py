"""
tests/integration/test_produtos_api.py
Testes de integração do módulo Produtos.
"""

import pytest

from backend.models.plataforma import Nicho, PlataformaCheckout

PRODUTOS_ENDPOINT = "/api/v1/produtos"


def _payload(nicho: Nicho, plataforma: PlataformaCheckout, **overrides) -> dict:
    base = {
        "nicho_id": nicho.id,
        "plataforma_checkout_id": plataforma.id,
        "nome": "Gelatide Pro",
        "cor_primaria": "#2D5A8E",
        "cor_secundaria": "#F7A800",
        "cor_background": "#FFFFFF",
        "variacoes": [
            {"quantidade_potes": 3, "checkout_identifier": "https://checkout.test/3", "url_imagem": "https://img.test/3.png"},
            {"quantidade_potes": 6, "checkout_identifier": "https://checkout.test/6", "url_imagem": "https://img.test/6.png"},
        ],
        "checkout_params": [],
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_create_produto_sucesso(client, sample_nicho, sample_plataforma):
    """Happy path: produto com variações → 201."""
    response = await client.post(PRODUTOS_ENDPOINT, json=_payload(sample_nicho, sample_plataforma))
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Gelatide Pro"
    assert data["nicho_id"] == sample_nicho.id
    assert len(data["variacoes"]) == 2


@pytest.mark.asyncio
async def test_create_produto_nicho_invalido(client, sample_plataforma):
    """nicho_id inexistente → 404."""
    response = await client.post(PRODUTOS_ENDPOINT, json={
        "nicho_id": 9999,
        "plataforma_checkout_id": sample_plataforma.id,
        "nome": "X", "cor_primaria": "#000", "cor_secundaria": "#FFF", "cor_background": "#FFF",
        "variacoes": [], "checkout_params": [],
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_produtos_vazio(client):
    """Sem produtos cadastrados → 200 com []."""
    response = await client.get(PRODUTOS_ENDPOINT)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_produto_nao_encontrado(client):
    """ID inexistente → 404."""
    response = await client.get(f"{PRODUTOS_ENDPOINT}/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_produtos_com_filtro_nicho(client, sample_nicho, sample_plataforma):
    """Filtro por nicho_id retorna apenas produtos do nicho."""
    await client.post(PRODUTOS_ENDPOINT, json=_payload(sample_nicho, sample_plataforma))
    response = await client.get(PRODUTOS_ENDPOINT, params={"nicho_id": sample_nicho.id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nicho_id"] == sample_nicho.id
