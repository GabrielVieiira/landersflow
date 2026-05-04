"""
conftest.py — Fixtures centralizadas do pytest.

Estratégia de isolamento:
- engine_test: SQLite in-memory por função → cada teste começa com DB zerado
- session_test: sessão assíncrona ligada ao engine_test
- client: AsyncClient do httpx com override de get_session (nunca toca o landersflow.db)
- mock_github: stub do PyGithub via pytest-mock
- Fixtures de dados: seeders reutilizáveis para nicho, plataforma, produto, templates etc.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.api.deps import get_session
from backend.main import app  # Importar app já carrega todos os models transitivamente
from backend.models.dominio import Dominio, StatusDNS
from backend.models.lander import Lander
from backend.models.plataforma import Nicho, PlataformaCheckout
from backend.models.produto import Produto, ProdutoVariacao
from backend.models.template import Template, TipoTemplate


# =============================================================================
# ENGINE E SESSÃO IN-MEMORY
# =============================================================================

@pytest_asyncio.fixture
async def engine_test() -> AsyncEngine:
    """Engine SQLite in-memory por teste — nunca toca o landersflow.db."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_test(engine_test: AsyncEngine) -> AsyncSession:
    """Sessão assíncrona isolada. Não commita automaticamente — controle manual nos testes."""
    SessionLocal = sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


# =============================================================================
# CLIENTE HTTP (FastAPI TestClient assíncrono)
# =============================================================================

@pytest_asyncio.fixture
async def client(session_test: AsyncSession) -> AsyncClient:
    """
    AsyncClient apontando para o app FastAPI com override da dependência get_session.
    Toda requisição usa o banco in-memory — zero efeito colateral no banco real.
    """
    async def _override_get_session():
        yield session_test

    app.dependency_overrides[get_session] = _override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# =============================================================================
# MOCKS DE SERVIÇOS EXTERNOS
# =============================================================================

@pytest.fixture
def mock_github(mocker):
    """
    Stub de github_service.get_template_folder.
    Lander retorna dict com index.html contendo {{headline}}.
    Offer retorna dict com offer.html contendo {{nome_produto}}.
    """
    lander_files = {"index.html": b"<html><body>{{headline}}</body></html>"}
    offer_files = {"offer.html": b"<html><body>{{nome_produto}}</body></html>"}

    mocker.patch(
        "backend.services.github_service.get_template_folder",
        side_effect=[lander_files, offer_files, lander_files, offer_files],
    )


# =============================================================================
# FIXTURES DE DADOS (seeders reutilizáveis)
# =============================================================================

@pytest_asyncio.fixture
async def sample_nicho(session_test: AsyncSession) -> Nicho:
    nicho = Nicho(sigla="EMAG", nome="Emagrecimento")
    session_test.add(nicho)
    await session_test.flush()
    return nicho


@pytest_asyncio.fixture
async def sample_plataforma(session_test: AsyncSession) -> PlataformaCheckout:
    plataforma = PlataformaCheckout(
        nome="Generic",
        slug_aplicacao="generic",
        integra_redtrack_offer=True,
        padrao_link_html='href="{url}"',
    )
    session_test.add(plataforma)
    await session_test.flush()
    return plataforma


@pytest_asyncio.fixture
async def sample_produto(
    session_test: AsyncSession,
    sample_nicho: Nicho,
    sample_plataforma: PlataformaCheckout,
) -> Produto:
    produto = Produto(
        nicho_id=sample_nicho.id,
        plataforma_checkout_id=sample_plataforma.id,
        nome="TestProd",
        cor_primaria="#FF0000",
        cor_secundaria="#00FF00",
        cor_background="#FFFFFF",
    )
    session_test.add(produto)
    await session_test.flush()

    # Variações mínimas exigidas (2, 3, 6)
    for qtd in (2, 3, 6):
        session_test.add(
            ProdutoVariacao(
                produto_id=produto.id,
                quantidade_potes=qtd,
                checkout_identifier=f"https://checkout.test/{qtd}",
                url_imagem=f"https://img.test/{qtd}.png",
            )
        )
    await session_test.flush()
    return produto


@pytest_asyncio.fixture
async def sample_dominio(session_test: AsyncSession, sample_nicho: Nicho) -> Dominio:
    dominio = Dominio(
        nicho_id=sample_nicho.id,
        url="testdomain.com",
        cloudflare_zone_id="zone-abc123",
        status_dns=StatusDNS.ACTIVE,
    )
    session_test.add(dominio)
    await session_test.flush()
    return dominio


# Fixtures de TipoTemplate
@pytest_asyncio.fixture
async def sample_tipo_lander(session_test: AsyncSession) -> TipoTemplate:
    tipo = TipoTemplate(nome="lander")
    session_test.add(tipo)
    await session_test.flush()
    return tipo


@pytest_asyncio.fixture
async def sample_tipo_offer(session_test: AsyncSession) -> TipoTemplate:
    tipo = TipoTemplate(nome="offer_section")
    session_test.add(tipo)
    await session_test.flush()
    return tipo


@pytest_asyncio.fixture
async def sample_template_index(session_test: AsyncSession, sample_tipo_lander: TipoTemplate) -> Template:
    t = Template(
        nome="Test Index",
        tipo_template_id=sample_tipo_lander.id,
        repo_github="lander/test",
    )
    session_test.add(t)
    await session_test.flush()
    return t


@pytest_asyncio.fixture
async def sample_template_offer(session_test: AsyncSession, sample_tipo_offer: TipoTemplate) -> Template:
    t = Template(
        nome="Test Offer",
        tipo_template_id=sample_tipo_offer.id,
        repo_github="offer_section/test",
    )
    session_test.add(t)
    await session_test.flush()
    return t


@pytest_asyncio.fixture
async def sample_lander_deployed(
    session_test: AsyncSession,
    sample_produto: Produto,
    sample_dominio: Dominio,
    sample_template_index: Template,
    sample_template_offer: Template,
) -> Lander:
    """Lander já deployada — usada para testar o status 409 no deploy."""
    lander = Lander(
        produto_id=sample_produto.id,
        template_index_id=sample_template_index.id,
        template_offer_id=sample_template_offer.id,
        dominio_id=sample_dominio.id,
        headline="Headline de Teste",
        vturb_preload="",
        vturb_script="",
        vturb_delay_segundos=750,
        url_final="https://testdomain.com/testprod/",
        redtrack_lander_id="rt-123",
    )
    session_test.add(lander)
    await session_test.flush()
    return lander
