"""
Engine SQLite assíncrono e fábrica de sessões.
Utiliza aiosqlite como driver para compatibilidade total com async/await do FastAPI.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings

settings = get_settings()

# Engine assíncrono com pool configurado para SQLite
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    connect_args={"check_same_thread": False},
    future=True,
)

# Fábrica de sessões assíncronas
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_db_and_tables() -> None:
    """
    Cria todas as tabelas no banco de dados na inicialização do app.
    Os modelos devem ser importados ANTES desta função ser chamada
    para que o metadata do SQLModel os reconheça.
    """
    # Importa todos os modelos para registrar no metadata
    from backend.models import (  # noqa: F401
        campanha,
        dominio,
        lander,
        plataforma,
        produto,
        template,
        traffic,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency FastAPI que fornece uma sessão assíncrona por request.
    Garante rollback em caso de exceção e fechamento ao final.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
