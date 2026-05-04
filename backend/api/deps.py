"""
Dependências FastAPI centralizadas.
Importar daqui em todos os handlers da api/v1/.
"""

from backend.database import get_session  # noqa: F401 — re-exportado como dependência FastAPI

__all__ = ["get_session"]
