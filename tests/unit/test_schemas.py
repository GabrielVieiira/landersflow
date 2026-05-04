"""
tests/unit/test_schemas.py

Testes de validação dos schemas Pydantic.
Garante que o contrato de entrada da API rejeita payloads inválidos.
"""

import pytest
from pydantic import ValidationError

from backend.schemas.lander import CompileLanderRequest

PAYLOAD_BASE = {
    "produto_id": 1,
    "template_index_id": 1,
    "template_offer_id": 2,
    "nome_produto": "Gelatide",
    "headline": "A promessa mais matadora",
    "vturb_preload": "",
    "vturb_script": "",
    "vturb_delay": "12:30",
    "nicho_id": 1,
    "dominio_id": 1,
}


def test_payload_valido_instancia_sem_erro():
    req = CompileLanderRequest(**PAYLOAD_BASE)
    assert req.produto_id == 1
    assert req.vturb_delay == "12:30"


def test_delay_invalido_lanca_validation_error():
    """Formato sem ':' deve ser rejeitado pelo field_validator antes de chegar ao service."""
    payload = {**PAYLOAD_BASE, "vturb_delay": "1230"}
    with pytest.raises(ValidationError) as exc_info:
        CompileLanderRequest(**payload)
    assert "Formato de delay inválido" in str(exc_info.value)


def test_delay_segundos_invalidos_lanca_validation_error():
    """Segundos >= 60 devem ser rejeitados."""
    payload = {**PAYLOAD_BASE, "vturb_delay": "12:60"}
    with pytest.raises(ValidationError):
        CompileLanderRequest(**payload)


def test_nome_arquivo_offer_nao_existe_mais_no_schema():
    """nome_arquivo_offer foi removido — payload com ele deve ser ignorado (extra='ignore')."""
    payload = {**PAYLOAD_BASE, "nome_arquivo_offer": "offer.html"}
    # Não deve lançar erro — campos extras são ignorados pelo Pydantic por padrão
    req = CompileLanderRequest(**payload)
    assert not hasattr(req, "nome_arquivo_offer")
