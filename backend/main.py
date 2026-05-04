"""
FastAPI Application — LanderFlow Backend

Entry point do sistema. Configura:
- Lifespan: criação das tabelas na inicialização
- CORS: permite requests do Streamlit frontend
- Routers: landers, produtos, templates, campanhas
- Documentação: OpenAPI com metadata completa
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.v1.router import api_router
from backend.config import get_settings
from backend.database import create_db_and_tables

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# LIFESPAN
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado na inicialização e shutdown da aplicação.
    Cria todas as tabelas do banco de dados na primeira execução.
    """
    logger.info("🚀 LanderFlow iniciando...")
    await create_db_and_tables()
    logger.info("✅ Banco de dados pronto.")
    logger.info(f"   Ambiente: {settings.app_env}")
    logger.info(f"   Nichos permitidos: {settings.nichos_lista}")
    yield
    logger.info("🛑 LanderFlow encerrando.")


# =============================================================================
# APLICAÇÃO
# =============================================================================

app = FastAPI(
    title="LanderFlow API",
    description=(
        "Sistema de automação para criação e deploy de Landing Pages.\n\n"
        "**Fluxo principal:**\n"
        "1. `POST /api/v1/landers/compile` — Compila templates Jinja2 para revisão (QA)\n"
        "2. `POST /api/v1/landers/deploy/{id}` — Deploy no GitHub Pages + RedTrack\n"
        "3. `POST /api/v1/campanhas` — Cria campanha no RedTrack com Traffic Channel\n\n"
        "**Repositórios de templates:** Lidos via PyGithub in-memory (sem escrita em disco)."
    ),
    version="0.1.0",
    contact={"name": "LanderFlow Team"},
    license_info={"name": "Privado"},
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# =============================================================================
# MIDDLEWARES
# =============================================================================

# CORS — permite que o Streamlit (frontend) faça requests ao backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,           # http://localhost:8501
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ROUTERS
# =============================================================================

API_PREFIX = "/api/v1"

app.include_router(api_router, prefix=API_PREFIX)



# =============================================================================
# ENDPOINTS UTILITÁRIOS
# =============================================================================

@app.get("/", tags=["Health"])
async def root() -> JSONResponse:
    """Health check e informações da API."""
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": "0.1.0",
            "status": "online",
            "environment": settings.app_env,
            "docs": "/docs",
        }
    )


@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check para monitoramento."""
    return JSONResponse(content={"status": "healthy"})
