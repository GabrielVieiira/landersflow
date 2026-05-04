"""
tests/integration/test_dominio.py

Testes de integração do modelo Dominio — foco na persistência correta do StatusDNS.

Por que este arquivo existe:
    Em produção, o banco pode conter valores inseridos por caminhos diferentes do ORM:
    seeds, migrações, backups, inserts manuais. O StatusDNS precisa ser lido corretamente
    independentemente de qual caminho escreveu o dado.

Testes:
    1. ORM -> ORM   : o caminho normal (create -> read via SQLModel)
    2. SQL raw -> ORM: o caminho externo (insert direto -> read via SQLModel)
                      Este e o teste que teria capturado o bug do 'active' vs 'ACTIVE'.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.dominio import Dominio, StatusDNS
from backend.models.plataforma import Nicho


# =============================================================================
# Teste 1 — ORM -> ORM (caminho normal do sistema)
# =============================================================================

@pytest.mark.asyncio
async def test_status_dns_roundtrip_via_orm(session_test: AsyncSession, sample_nicho: Nicho):
    """
    Caminho normal: cria Dominio via ORM com StatusDNS.ACTIVE e le de volta.
    Garante que o campo sobrevive ao ciclo write -> flush -> read sem perda de tipo.
    """
    dominio = Dominio(
        nicho_id=sample_nicho.id,
        url="orm-test.com",
        cloudflare_zone_id="zone-orm-001",
        status_dns=StatusDNS.ACTIVE,
    )
    session_test.add(dominio)
    await session_test.flush()

    # Expira o cache para forcar releitura do banco
    await session_test.refresh(dominio)

    assert dominio.status_dns == StatusDNS.ACTIVE
    assert dominio.status_dns == "active"  # str, Enum herda de str — comparacao por valor


# =============================================================================
# Teste 2 — SQL raw -> ORM (caminho externo: seeds, migracoes, backups)
# =============================================================================

@pytest.mark.asyncio
async def test_status_dns_lido_de_insert_raw_sql(
    engine_test: AsyncEngine,
    session_test: AsyncSession,
    sample_nicho: Nicho,
):
    """
    Regressao do bug 'active is not among the defined enum values'.

    Simula dados inseridos fora do ORM (seed script, migration, insert manual)
    com o valor em lowercase ('active', 'pending', 'error') e verifica que o
    SQLModel consegue reconstruir o enum corretamente na leitura.

    Este e o teste que teria capturado o bug antes de chegar em producao.
    """
    # Captura o ID antes de qualquer expire_all para evitar lazy load fora do contexto async
    nicho_id = sample_nicho.id

    # Insere diretamente via SQL, sem passar pelo ORM — simula seed/migracao
    async with engine_test.connect() as conn:
        await conn.execute(
            text(
                "INSERT INTO dominio (nicho_id, url, cloudflare_zone_id, status_dns) "
                "VALUES (:nicho_id, :url, :zone, :status)"
            ),
            {
                "nicho_id": nicho_id,
                "url": "seed-test.com",
                "zone": "zone-seed-001",
                "status": "active",
            },
        )
        await conn.commit()

    # Busca o ID via engine (evita aviso do SQLModel sobre session.execute)
    async with engine_test.connect() as conn:
        result = await conn.execute(
            text("SELECT id FROM dominio WHERE url = 'seed-test.com'")
        )
        dominio_id = result.scalar_one()

    session_test.expire_all()
    dominio = await session_test.get(Dominio, dominio_id)

    assert dominio is not None
    assert dominio.status_dns == StatusDNS.ACTIVE, (
        f"Esperado StatusDNS.ACTIVE, obtido: {dominio.status_dns!r}. "
        "Possivel regressao do bug 'active is not among the defined enum values'."
    )

    # Testa os outros valores tambem para cobertura completa
    for valor_raw, membro_esperado in [
        ("pending", StatusDNS.PENDING),
        ("error",   StatusDNS.ERROR),
    ]:
        async with engine_test.connect() as conn:
            await conn.execute(
                text(
                    "INSERT INTO dominio (nicho_id, url, cloudflare_zone_id, status_dns) "
                    "VALUES (:nicho_id, :url, :zone, :status)"
                ),
                {
                    "nicho_id": nicho_id,
                    "url": f"seed-{valor_raw}.com",
                    "zone": f"zone-{valor_raw}",
                    "status": valor_raw,
                },
            )
            await conn.commit()

        async with engine_test.connect() as conn:
            result = await conn.execute(
                text(f"SELECT id FROM dominio WHERE url = 'seed-{valor_raw}.com'")
            )
            did = result.scalar_one()

        session_test.expire_all()
        d = await session_test.get(Dominio, did)

        assert d.status_dns == membro_esperado, (
            f"Valor raw '{valor_raw}' nao foi convertido para {membro_esperado}. "
            "Verifique a configuracao da coluna status_dns em dominio.py."
        )
