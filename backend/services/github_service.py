"""
GitHub Service — Deploy e leitura de templates via Git SSH.

Todas as operações usam a mesma chave SSH (deploy_bot):

1. LEITURA DE TEMPLATES (get_template_folder)
   - Clona o repositório 'layouts' localmente via SSH (uma vez; reutiliza em seguida).
   - Lê a pasta do template diretamente do disco.
   - Retorna dict {caminho_relativo: conteudo_bytes}.
   - NÃO usa PyGithub nem GITHUB_TOKEN.

2. DEPLOY DE LANDERS (deploy_lander_files)
   - Clona o repositório de destino do nicho via SSH.
   - Escreve os arquivos, faz commit e push.
   - Reutiliza o clone local entre deploys.

Credenciais:
   - Tudo via SSH key em DEPLOY_SSH_KEY_PATH (~/.ssh/deploy_bot)
   - GITHUB_OWNER é necessário para montar as URLs SSH dos repos
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# HELPERS SSH / GIT
# =============================================================================

def _get_ssh_env() -> dict:
    """
    Monta as variáveis de ambiente para o processo Git usar a chave SSH do bot.
    Garante que o git não pedirá senha interativa e usará a chave correta.
    """
    ssh_key = Path(settings.deploy_ssh_key_path).expanduser().resolve()
    git_ssh_cmd = (
        f'ssh -i "{ssh_key}" '
        f'-o StrictHostKeyChecking=no '
        f'-o IdentitiesOnly=yes'
    )
    return {**os.environ, "GIT_SSH_COMMAND": git_ssh_cmd}


def _run_git(args: list[str], cwd: Path, env: dict) -> str:
    """
    Executa um comando git e retorna o stdout.
    Lança RuntimeError se o processo falhar.
    """
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} falhou:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
    return result.stdout.strip()


def _repo_tem_commits(local_path: Path, env: dict) -> bool:
    """Retorna True se o repo local já possui pelo menos um commit."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(local_path),
        env=env,
        capture_output=True,
    )
    return result.returncode == 0


def _get_or_clone_repo(repo_url: str, local_path: Path, env: dict) -> None:
    """
    Garante que o repositório está disponível localmente.
    - Se não existir: clona.
    - Se já existir com commits: faz git pull --rebase para sincronizar.
    - Se já existir mas vazio (sem commits): pula o pull — o repo foi
      clonado antes do primeiro commit/push e não tem branch ainda.
    """
    if local_path.exists() and (local_path / ".git").exists():
        if _repo_tem_commits(local_path, env):
            logger.info(f"Repo ja clonado em {local_path}. Fazendo pull...")
            _run_git(["pull", "origin", "main", "--rebase"], cwd=local_path, env=env)
        else:
            logger.info(f"Repo em {local_path} vazio (sem commits). Pulando pull.")
    else:
        if local_path.exists():
            logger.warning(f"Pasta {local_path} existe mas nao e um repo git. Removendo...")
            shutil.rmtree(local_path)
        logger.info(f"Clonando {repo_url} -> {local_path}")
        _run_git(["clone", repo_url, str(local_path)], cwd=local_path.parent, env=env)


def _clone_root() -> Path:
    """Retorna (e cria se necessário) o diretório raiz dos clones locais."""
    root = Path(settings.deploy_local_clone_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


# =============================================================================
# LEITURA DE TEMPLATES (layouts repo — via SSH, sem PyGithub)
# =============================================================================

def get_template_folder(repo_github: str) -> dict[str, bytes]:
    """
    Lê todos os arquivos de uma pasta de template do repo 'layouts' via SSH.

    O campo repo_github do Template armazena o caminho da pasta dentro do repo:
        - 'lander/cnn'           → layouts/lander/cnn/
        - 'offer_section/padrao' → layouts/offer_section/padrao/

    Fluxo:
        1. Clona (ou atualiza) o repo 'layouts' localmente via SSH.
        2. Lê recursivamente todos os arquivos da sub-pasta do template.
        3. Retorna dict {caminho_relativo: conteudo_bytes}.

    Args:
        repo_github: Caminho da pasta no repo (ex: 'lander/cnn', 'offer_section/padrao')

    Returns:
        Dict com {caminho_relativo_dentro_da_pasta: conteudo_bytes}
        Ex: {
            'index.html': b'<!DOCTYPE html>...',
            'style.css':  b'body { ... }',
            'assets/logo.png': b'...',
        }

    Raises:
        ValueError: Se GITHUB_OWNER ou DEPLOY_SSH_KEY_PATH não estiverem configurados
        FileNotFoundError: Se a pasta do template não existir no repo
        RuntimeError: Em caso de falha no clone/pull
    """
    if not settings.github_owner:
        raise ValueError(
            "GITHUB_OWNER não configurado. Verifique o arquivo .env."
        )
    if not settings.deploy_ssh_key_path:
        raise ValueError(
            "DEPLOY_SSH_KEY_PATH não configurado. Verifique o arquivo .env."
        )

    layouts_url = (
        f"git@github.com:{settings.github_owner}/{settings.github_repo_layouts}.git"
    )
    local_path = _clone_root() / settings.github_repo_layouts
    env = _get_ssh_env()

    logger.info(f"Sincronizando repo layouts -> {local_path}")
    _get_or_clone_repo(layouts_url, local_path, env)

    # Lê os arquivos da sub-pasta do template
    template_path = local_path / repo_github
    if not template_path.exists():
        raise FileNotFoundError(
            f"Pasta de template não encontrada: {template_path}\n"
            f"Verifique se '{repo_github}' existe no repo '{settings.github_repo_layouts}'."
        )

    result: dict[str, bytes] = {}
    for file_path in template_path.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(template_path)
            # Normaliza separadores para '/' em qualquer OS
            key = str(relative).replace("\\", "/")
            result[key] = file_path.read_bytes()
            logger.debug(f"  Arquivo lido: {key} ({len(result[key])} bytes)")

    total_files = len(result)
    total_bytes = sum(len(v) for v in result.values())
    logger.info(f"Template carregado: {repo_github} | {total_files} arquivo(s), {total_bytes:,} bytes")

    return result


def get_template_content(repo_github: str, *args, **kwargs) -> str:
    """
    [DEPRECATED] Retorna apenas o conteúdo HTML principal de um template.
    Use get_template_folder() para obter todos os arquivos.

    Detecta automaticamente o nome do arquivo principal:
        - Se repo_github começa com 'lander/'        → arquivo é 'index.html'
        - Se repo_github começa com 'offer_section/' → arquivo é 'offer.html'
    """
    logger.warning(
        "get_template_content() está deprecated. Use get_template_folder()."
    )
    files = get_template_folder(repo_github)

    main_file = "index.html" if repo_github.startswith("lander/") else "offer.html"

    if main_file not in files:
        raise FileNotFoundError(
            f"Arquivo principal '{main_file}' não encontrado em {repo_github}/"
        )

    return files[main_file].decode("utf-8")


# =============================================================================
# DEPLOY DE LANDERS (repos de destino — via SSH)
# =============================================================================

def deploy_lander_files(
    dest_repo_name: str,
    files: dict[str, bytes | str],
    commit_message: str = "auto: deploy lander",
    branch: str = "main",
) -> str:
    """
    Faz deploy de múltiplos arquivos em um repositório GitHub Pages via SSH.

    Os caminhos em `files` são relativos à raiz do repo de destino.
    O montador (lander_service) já entrega os arquivos com os paths corretos:
        - 'lander-7/index.html'
        - 'lander-7/style.css'
        - 'lander-7/offer/index.html'
        - 'lander-7/offer/style.css'

    Args:
        dest_repo_name: Nome do repo de destino (sem owner). Ex: 'cyberflow-lat'
        files: Dict {caminho_no_repo: conteudo (bytes ou str)}
        commit_message: Mensagem do commit
        branch: Branch de destino (default: 'main')

    Returns:
        URL base do GitHub Pages. Ex: 'https://cyberflow.lat'

    Raises:
        ValueError: Se variáveis necessárias não estiverem configuradas
        RuntimeError: Em caso de falha no clone, escrita ou push
    """
    if not settings.github_owner:
        raise ValueError(
            "GITHUB_OWNER nao configurado. Verifique o arquivo .env."
        )
    if not settings.deploy_ssh_key_path:
        raise ValueError(
            "DEPLOY_SSH_KEY_PATH nao configurado. Verifique o arquivo .env."
        )
    if not settings.deploy_local_clone_dir:
        raise ValueError(
            "DEPLOY_LOCAL_CLONE_DIR nao configurado. Verifique o arquivo .env."
        )

    repo_url = f"git@github.com:{settings.github_owner}/{dest_repo_name}.git"
    local_path = _clone_root() / dest_repo_name
    env = _get_ssh_env()

    logger.info(f"Iniciando deploy -> {dest_repo_name} | {len(files)} arquivo(s)")

    # 1. Garante clone local atualizado
    _get_or_clone_repo(repo_url, local_path, env)

    # 2. Escreve os arquivos no clone local
    for file_path, content in files.items():
        target = local_path / file_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)

        logger.info(f"  Escrito: {file_path}")

    # 3. Configura identidade do bot (escopo local do repo)
    _run_git(["config", "user.name", settings.deploy_bot_name], cwd=local_path, env=env)
    _run_git(["config", "user.email", settings.deploy_bot_email], cwd=local_path, env=env)

    # 4. Verifica se há mudanças reais antes de commitar
    status = _run_git(["status", "--porcelain"], cwd=local_path, env=env)
    if not status:
        logger.info("Nenhuma alteracao detectada. Deploy ignorado.")
        return _build_pages_url(dest_repo_name)

    # 5. git add → commit → push
    _run_git(["add", "."], cwd=local_path, env=env)
    _run_git(["commit", "-m", commit_message], cwd=local_path, env=env)
    # -u configura o upstream tracking — necessário no primeiro push de um repo novo.
    # Em pushes subsequentes é inofensivo (apenas reafirma o tracking).
    _run_git(["push", "-u", "origin", branch], cwd=local_path, env=env)

    pages_url = _build_pages_url(dest_repo_name)
    logger.info(f"Deploy concluido. GitHub Pages: {pages_url}")

    return pages_url


def _build_pages_url(dest_repo_name: str) -> str:
    """
    Monta a URL do GitHub Pages a partir do nome do repositório.
    Convenção: 'cyberflow-lat' → 'https://cyberflow.lat'
    """
    return f"https://{dest_repo_name.replace('-', '.').rstrip('.')}"
