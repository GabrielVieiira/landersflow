"""
tests/unit/test_compiler.py

Testes unitários das funções puras do compilador Jinja2.
Não precisam de banco de dados ou serviços externos.
"""

import pytest
from jinja2 import UndefinedError

from backend.services.compiler import (
    build_button_attrs,
    parse_vturb_delay,
    render_template,
)
from backend.models.produto import ProdutoVariacao


# =============================================================================
# parse_vturb_delay — 6 testes
# =============================================================================

def test_delay_12_30_retorna_750():
    """Regra documentada: (Minutos * 60) + Segundos."""
    assert parse_vturb_delay("12:30") == 750


def test_delay_zero():
    assert parse_vturb_delay("00:00") == 0


def test_delay_apenas_minutos():
    assert parse_vturb_delay("45:00") == 2700


def test_delay_apenas_segundos():
    assert parse_vturb_delay("00:30") == 30


def test_delay_formato_invalido_sem_dois_pontos():
    with pytest.raises(ValueError, match="Formato de delay inválido"):
        parse_vturb_delay("1230")


def test_delay_segundos_maiores_que_59():
    with pytest.raises(ValueError, match="Segundos inválidos"):
        parse_vturb_delay("12:60")


def test_delay_letras():
    with pytest.raises(ValueError, match="Formato de delay inválido"):
        parse_vturb_delay("AB:CD")


# =============================================================================
# build_button_attrs — 3 testes
# =============================================================================

from dataclasses import dataclass

@dataclass
class _FakeVariacao:
    """Substitui ProdutoVariacao nos testes unitários para evitar dependência de SQLModel."""
    quantidade_potes: int
    checkout_identifier: str
    url_imagem: str = ""

def _make_variacao(qtd: int, url: str) -> _FakeVariacao:
    return _FakeVariacao(quantidade_potes=qtd, checkout_identifier=url)


def test_button_attrs_padrao_url():
    """Plataformas genéricas usam href="{url}"."""
    v = _make_variacao(3, "https://checkout.example.com/prod")
    result = build_button_attrs('href="{url}"', v)
    assert result == 'href="https://checkout.example.com/prod"'


def test_button_attrs_padrao_qtd():
    """ClickBank usa data-click-path com qtd."""
    v = _make_variacao(3, "https://checkout.example.com/prod")
    result = build_button_attrs('href="#" data-click-path="/click/{qtd}"', v)
    assert result == 'href="#" data-click-path="/click/3"'


def test_button_attrs_alias_url_checkout():
    """Alias url_checkout deve funcionar igual a url."""
    v = _make_variacao(6, "https://cb.example.com/buy")
    result = build_button_attrs('href="{url_checkout}"', v)
    assert result == 'href="https://cb.example.com/buy"'


# =============================================================================
# render_template (Jinja2) — 3 testes
# =============================================================================

def test_render_substitui_placeholder():
    html = render_template("<h1>{{headline}}</h1>", {"headline": "Título Incrível"})
    assert html == "<h1>Título Incrível</h1>"
    assert "{{" not in html


def test_render_multiplos_placeholders():
    tmpl = "{{nome_produto}} — {{headline}}"
    ctx = {"nome_produto": "Gelatide", "headline": "Perca 10kg em 30 dias"}
    result = render_template(tmpl, ctx)
    assert result == "Gelatide — Perca 10kg em 30 dias"


def test_render_strict_undefined_lanca_erro():
    """StrictUndefined deve lançar erro se o template usar variável fora do contexto."""
    with pytest.raises(UndefinedError):
        render_template("<p>{{chave_inexistente}}</p>", {})
