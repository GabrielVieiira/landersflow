"""
Configurações centralizadas via pydantic-settings.
Carrega automaticamente do arquivo .env (ou variáveis de ambiente).
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- APP ---
    app_name: str = "LanderFlow"
    app_env: str = "development"
    secret_key: str = "dev-secret-key-change-in-production"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:8501"

    # --- DATABASE ---
    database_url: str = "sqlite+aiosqlite:///./landersflow.db"

    # --- GITHUB ---
    github_owner: str = ""                        # Username/org dona dos repos
    github_repo_layouts: str = "layouts"          # Repo com todos os templates

    # --- DEPLOY SSH — Escrita nos repos de páginas (Git + SSH bot) ---
    deploy_ssh_key_path: str = "~/.ssh/deploy_bot"          # Chave privada ED25519 do bot
    deploy_local_clone_dir: str = "/tmp/landersflow-clones" # Dir local para clones temporários
    deploy_bot_name: str = "bot"                # Nome do bot nos commits
    deploy_bot_email: str = "bot@landersflow.internal"      # Email do bot nos commits
    # Repo de teste usado exclusivamente pelo smoke test (tests/smoke/test_ssh_smoke.py).
    # Valida o fluxo completo de commit + push via SSH antes de usar em produção.
    # Deixe vazio para pular o Teste 3 do smoke test.
    smoke_test_deploy_repo: str = "test"

    # --- REDTRACK ---
    redtrack_api_key: str = ""
    redtrack_api_url: str = "https://api.redtrack.io"

    # --- BUSINESS ---
    nichos_permitidos: str = "EMAG,TT,ML,T2D,ED,PT,NPT,VIS"

    # --- DEPLOY POLLING ---
    deploy_polling_timeout: int = 300   # segundos
    deploy_polling_interval: int = 15   # segundos

    @property
    def nichos_lista(self) -> List[str]:
        """Retorna os nichos permitidos como lista."""
        return [n.strip().upper() for n in self.nichos_permitidos.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de configurações. Cacheado para evitar releituras do disco."""
    return Settings()
