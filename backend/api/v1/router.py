"""
Router master da API v1.
Todos os módulos migrados para a nova arquitetura (api/ + schemas/ + services/ + repositories/).
"""

from fastapi import APIRouter

from backend.api.v1 import campanhas, landers, produtos, templates

api_router = APIRouter()

api_router.include_router(landers.router)
api_router.include_router(produtos.router)
api_router.include_router(templates.router)
api_router.include_router(campanhas.router)
