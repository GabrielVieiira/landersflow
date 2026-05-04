"""
tests/unit/test_github_service.py

Testes unitários do github_service.py.
NÃO fazem conexão real com o GitHub — subprocess.run é mockado.

Cobertos:
  - Construção correta do comando GIT_SSH_COMMAND (com aspas no path — bug real do Windows)
  - _get_or_clone_repo: comportamento quando repo não existe (clone) e quando existe (pull)
  - get_template_folder: erro quando GITHUB_OWNER não está configurado
  - get_template_folder: erro quando pasta do template não existe no repo
  - deploy_lander_files: skip silencioso quando git status --porcelain retorna vazio
  - deploy_lander_files: executa add/commit/push quando há mudanças
"""

from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import backend.services.github_service as svc


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Garante que o cache de settings é limpo entre testes."""
    from backend.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def fake_settings(tmp_path):
    """Settings mínimos para os testes — sem credenciais reais."""
    key_path = tmp_path / ".ssh" / "deploy_bot"
    key_path.parent.mkdir(parents=True)
    key_path.touch()  # arquivo vazio — não é usado de verdade

    clone_dir = tmp_path / "clones"
    clone_dir.mkdir()

    mock_settings = MagicMock()
    mock_settings.github_owner = "meu-usuario"
    mock_settings.github_repo_layouts = "layouts"
    mock_settings.deploy_ssh_key_path = str(key_path)
    mock_settings.deploy_local_clone_dir = str(clone_dir)
    mock_settings.deploy_bot_name = "landersflow-bot"
    mock_settings.deploy_bot_email = "bot@landersflow.com"
    return mock_settings


# =============================================================================
# _get_ssh_env — constrói GIT_SSH_COMMAND corretamente
# =============================================================================

class TestGetSshEnv:
    def test_chave_com_espaco_no_path_tem_aspas(self, tmp_path):
        """Bug real do Windows: path com contrabarras/espaços precisa de aspas."""
        key_path = tmp_path / "minha chave" / "deploy_bot"
        key_path.parent.mkdir(parents=True)
        key_path.touch()

        with patch.object(svc, "settings") as mock_s:
            mock_s.deploy_ssh_key_path = str(key_path)
            env = svc._get_ssh_env()

        cmd = env["GIT_SSH_COMMAND"]
        # O caminho DEVE estar entre aspas duplas
        assert f'ssh -i "{key_path.resolve()}"' in cmd

    def test_flags_obrigatorias_presentes(self, tmp_path):
        """StrictHostKeyChecking=no evita prompt interativo; IdentitiesOnly=yes garante chave certa."""
        key_path = tmp_path / "deploy_bot"
        key_path.touch()

        with patch.object(svc, "settings") as mock_s:
            mock_s.deploy_ssh_key_path = str(key_path)
            env = svc._get_ssh_env()

        cmd = env["GIT_SSH_COMMAND"]
        assert "-o StrictHostKeyChecking=no" in cmd
        assert "-o IdentitiesOnly=yes" in cmd

    def test_chave_sem_espaco_tambem_funciona(self, tmp_path):
        """Paths simples (sem espaço) também devem estar entre aspas — consistência."""
        key_path = tmp_path / "deploy_bot"
        key_path.touch()

        with patch.object(svc, "settings") as mock_s:
            mock_s.deploy_ssh_key_path = str(key_path)
            env = svc._get_ssh_env()

        # As aspas devem estar presentes independentemente do path
        assert '"' in env["GIT_SSH_COMMAND"]


# =============================================================================
# _get_or_clone_repo — clone vs. pull
# =============================================================================

class TestGetOrCloneRepo:
    def test_clona_quando_pasta_nao_existe(self, tmp_path):
        """Se o diretório local não existe, deve chamar git clone."""
        repo_url = "git@github.com:owner/repo.git"
        local_path = tmp_path / "repo"  # Não existe ainda
        env = {}

        with patch.object(svc, "_run_git") as mock_git:
            svc._get_or_clone_repo(repo_url, local_path, env)

        mock_git.assert_called_once_with(
            ["clone", repo_url, str(local_path)],
            cwd=local_path.parent,
            env=env,
        )

    def test_faz_pull_quando_repo_ja_existe(self, tmp_path):
        """Se .git existe e há commits, deve fazer git pull --rebase em vez de clone."""
        repo_url = "git@github.com:owner/repo.git"
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / ".git").mkdir()
        env = {}

        with patch.object(svc, "_run_git") as mock_git:
            with patch.object(svc, "_repo_tem_commits", return_value=True):
                svc._get_or_clone_repo(repo_url, local_path, env)

        mock_git.assert_called_once_with(
            ["pull", "origin", "main", "--rebase"],
            cwd=local_path,
            env=env,
        )

    def test_remove_pasta_corrompida_antes_de_clonar(self, tmp_path):
        """Pasta existe mas sem .git (corrompida) → deve remover e clonar."""
        repo_url = "git@github.com:owner/repo.git"
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / "arquivo_orfao.txt").write_text("lixo")
        env = {}

        with patch.object(svc, "_run_git") as mock_git:
            svc._get_or_clone_repo(repo_url, local_path, env)

        assert not (local_path / "arquivo_orfao.txt").exists()
        mock_git.assert_called_once()
        assert mock_git.call_args[0][0][0] == "clone"

    def test_pula_pull_quando_repo_vazio(self, tmp_path):
        """Repo clonado mas sem commits (novo/vazio) → não tenta git pull (evita falha)."""
        local_path = tmp_path / "repo"
        local_path.mkdir()
        (local_path / ".git").mkdir()
        env = {}

        with patch.object(svc, "_run_git") as mock_git:
            with patch.object(svc, "_repo_tem_commits", return_value=False):
                svc._get_or_clone_repo("git@github.com:owner/repo.git", local_path, env)

        mock_git.assert_not_called()  # Nenhum pull deve ter sido chamado


# =============================================================================
# get_template_folder — validações de entrada e leitura de arquivos
# =============================================================================

class TestGetTemplateFolder:
    def test_lanca_erro_sem_github_owner(self):
        """GITHUB_OWNER vazio deve lançar ValueError descritivo."""
        with patch.object(svc, "settings") as mock_s:
            mock_s.github_owner = ""
            mock_s.deploy_ssh_key_path = "/qualquer/chave"

            with pytest.raises(ValueError, match="GITHUB_OWNER"):
                svc.get_template_folder("lander/cnn")

    def test_lanca_erro_sem_ssh_key(self):
        """DEPLOY_SSH_KEY_PATH vazio deve lançar ValueError descritivo."""
        with patch.object(svc, "settings") as mock_s:
            mock_s.github_owner = "meu-usuario"
            mock_s.deploy_ssh_key_path = ""

            with pytest.raises(ValueError, match="DEPLOY_SSH_KEY_PATH"):
                svc.get_template_folder("lander/cnn")

    def test_lanca_erro_pasta_template_nao_existe(self, tmp_path, fake_settings):
        """Se a pasta do template não existir no clone, lança FileNotFoundError."""
        clone_root = Path(fake_settings.deploy_local_clone_dir)
        # Cria o repo clonado mas SEM a pasta do template
        layouts_dir = clone_root / "layouts"
        layouts_dir.mkdir()
        (layouts_dir / ".git").mkdir()

        with patch.object(svc, "settings", fake_settings):
            with patch.object(svc, "_get_or_clone_repo"):  # Simula clone OK
                with pytest.raises(FileNotFoundError, match="lander/template-inexistente"):
                    svc.get_template_folder("lander/template-inexistente")

    def test_retorna_dict_com_arquivos_corretos(self, tmp_path, fake_settings):
        """Leitura correta de arquivos com caminhos relativos normalizados."""
        clone_root = Path(fake_settings.deploy_local_clone_dir)
        # Cria estrutura de template simulada
        template_dir = clone_root / "layouts" / "lander" / "cnn"
        template_dir.mkdir(parents=True)
        (template_dir / "index.html").write_bytes(b"<h1>Ola</h1>")
        (template_dir / "style.css").write_bytes(b"body{}")
        subdir = template_dir / "assets"
        subdir.mkdir()
        (subdir / "logo.png").write_bytes(b"\x89PNG")

        layouts_git = clone_root / "layouts"
        layouts_git.mkdir(exist_ok=True)
        (layouts_git / ".git").mkdir(exist_ok=True)

        with patch.object(svc, "settings", fake_settings):
            with patch.object(svc, "_get_or_clone_repo"):
                result = svc.get_template_folder("lander/cnn")

        assert "index.html" in result
        assert "style.css" in result
        assert "assets/logo.png" in result  # Separador normalizado para '/'
        assert result["index.html"] == b"<h1>Ola</h1>"


# =============================================================================
# deploy_lander_files — fluxo de commit e push
# =============================================================================

class TestDeployLanderFiles:
    def _make_repo(self, clone_root: Path, repo_name: str) -> Path:
        """Cria estrutura mínima de repo Git local."""
        repo = clone_root / repo_name
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()
        return repo

    def test_skip_quando_sem_mudancas(self, tmp_path, fake_settings):
        """git status --porcelain vazio → não faz commit, retorna URL mesmo assim."""
        self._make_repo(Path(fake_settings.deploy_local_clone_dir), "cyberflow-lat")

        with patch.object(svc, "settings", fake_settings):
            with patch.object(svc, "_get_or_clone_repo"):
                with patch.object(svc, "_run_git", return_value="") as mock_git:
                    # status vazio = sem mudanças
                    url = svc.deploy_lander_files(
                        "cyberflow-lat",
                        {"index.html": b"<h1>ok</h1>"},
                    )

        # Deve retornar a URL mesmo sem commit
        assert url == "https://cyberflow.lat"
        # Apenas config + status foram chamados (add/commit/push NÃO)
        chamadas = [c[0][0] for c in mock_git.call_args_list]
        assert "add" not in chamadas
        assert "commit" not in chamadas
        assert "push" not in chamadas

    def test_executa_add_commit_push_quando_ha_mudancas(self, tmp_path, fake_settings):
        """git status com conteúdo → fluxo completo de commit."""
        self._make_repo(Path(fake_settings.deploy_local_clone_dir), "cyberflow-lat")

        def mock_git_side_effect(args, **kwargs):
            if args[0] == "status":
                return "M lander-7/index.html"  # Simula arquivo modificado
            return ""

        with patch.object(svc, "settings", fake_settings):
            with patch.object(svc, "_get_or_clone_repo"):
                with patch.object(svc, "_run_git", side_effect=mock_git_side_effect) as mock_git:
                    svc.deploy_lander_files(
                        "cyberflow-lat",
                        {"lander-7/index.html": b"<html/>"},
                        commit_message="auto: deploy lander #7",
                    )

        # c[0][0] é a lista de args do git (ex: ['add', '.']), pegamos o verbo [0]
        verbos = [c[0][0][0] for c in mock_git.call_args_list]
        assert "add" in verbos
        assert "commit" in verbos
        assert "push" in verbos

    def test_commit_tem_mensagem_correta(self, tmp_path, fake_settings):
        """A mensagem de commit passada deve ser usada no git commit."""
        self._make_repo(Path(fake_settings.deploy_local_clone_dir), "cyberflow-lat")

        def mock_git_side_effect(args, **kwargs):
            if args[0] == "status":
                return "M algo.html"
            return ""

        with patch.object(svc, "settings", fake_settings):
            with patch.object(svc, "_get_or_clone_repo"):
                with patch.object(svc, "_run_git", side_effect=mock_git_side_effect) as mock_git:
                    svc.deploy_lander_files(
                        "cyberflow-lat",
                        {"index.html": b"x"},
                        commit_message="deploy: lander-echozen-7",
                    )

        commit_call = next(
            c for c in mock_git.call_args_list if c[0][0][0] == "commit"
        )
        assert "deploy: lander-echozen-7" in commit_call[0][0]

    def test_lanca_erro_sem_github_owner(self):
        """GITHUB_OWNER vazio deve impedir o deploy."""
        with patch.object(svc, "settings") as mock_s:
            mock_s.github_owner = ""
            mock_s.deploy_ssh_key_path = "/chave"
            mock_s.deploy_local_clone_dir = "/clones"

            with pytest.raises(ValueError, match="GITHUB_OWNER"):
                svc.deploy_lander_files("cyberflow-lat", {})
