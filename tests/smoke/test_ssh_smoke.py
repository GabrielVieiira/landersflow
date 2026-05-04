"""
tests/smoke/test_ssh_smoke.py

Smoke Test de Integração SSH — requer credenciais reais e conexão com a internet.

NÃO faz parte da suíte pytest automática.

Execução manual:
    poetry run python tests/smoke/test_ssh_smoke.py

O que este script valida:
    1. Autenticação SSH com o GitHub (a chave deploy_bot funciona)
    2. Clone do repositório 'layouts' via SSH (leitura de templates)
    3. Clone + commit + push em repo de teste (fluxo de deploy)

Pré-requisitos:
    - Arquivo .env preenchido com GITHUB_OWNER e DEPLOY_SSH_KEY_PATH
    - Chave pública registrada na conta GitHub do bot
    - Variável SMOKE_DEPLOY_REPO no .env (repo para testar o deploy)
      Exemplo: SMOKE_DEPLOY_REPO=cyberflow-lat (deve existir no GitHub)
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Adiciona a raiz do projeto ao path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import get_settings
from backend.services import github_service as svc

# ---------------------------------------------------------------------------
# Helpers de saída
# ---------------------------------------------------------------------------

def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")

def _fail(msg: str, error: str = "") -> None:
    print(f"  [FALHOU] {msg}")
    if error:
        print(f"     Detalhe: {error}")

def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def _section(title: str) -> None:
    print(f"\n  --- {title} ---")


# ---------------------------------------------------------------------------
# Teste 1: Autenticação SSH com o GitHub
# ---------------------------------------------------------------------------

def test_ssh_autenticacao(settings) -> bool:
    """
    Roda: ssh -i <chave> -o StrictHostKeyChecking=no -T git@github.com
    O GitHub retorna exit code 1 mesmo quando a autenticação funciona,
    mas o stderr contém "Hi <usuario>!" — esse é o sinal de sucesso.
    """
    _section("Teste 1: Autenticação SSH com o GitHub")

    ssh_key = Path(settings.deploy_ssh_key_path).expanduser().resolve()

    if not ssh_key.exists():
        _fail(
            "Chave SSH não encontrada",
            f"Esperado em: {ssh_key}\n"
            f"     Verifique DEPLOY_SSH_KEY_PATH no .env"
        )
        return False

    _ok(f"Chave SSH encontrada: {ssh_key}")

    result = subprocess.run(
        [
            "ssh",
            "-i", str(ssh_key),
            "-o", "StrictHostKeyChecking=no",
            "-o", "IdentitiesOnly=yes",
            "-T",
            "git@github.com",
        ],
        capture_output=True,
        text=True,
    )

    # GitHub retorna "Hi <usuario>!" no stderr com exit code 1
    stderr = result.stderr.strip()
    if "Hi " in stderr and "!" in stderr:
        _ok(f"Autenticação OK — GitHub respondeu: {stderr}")
        return True
    elif "Permission denied" in stderr:
        _fail(
            "Permissão negada pelo GitHub",
            f"{stderr}\n"
            "     Verifique se a chave pública está registrada na conta do bot no GitHub."
        )
        return False
    elif "not accessible" in stderr or "No such file" in stderr:
        _fail(
            "Chave SSH não acessível",
            f"{stderr}\n"
            "     O caminho da chave está incorreto ou há problema de permissão no arquivo."
        )
        return False
    else:
        _fail(f"Resposta inesperada do GitHub", stderr)
        return False


# ---------------------------------------------------------------------------
# Teste 2: Clone do repositório 'layouts' (leitura de templates)
# ---------------------------------------------------------------------------

def test_clone_layouts(settings) -> bool:
    """
    Testa o fluxo real de get_template_folder:
    clona (ou atualiza) o repo 'layouts' e lê uma pasta de template.
    """
    _section("Teste 2: Clone do repositório 'layouts' (leitura de templates)")

    if not settings.github_owner:
        _fail("GITHUB_OWNER não configurado no .env")
        return False

    layouts_url = f"git@github.com:{settings.github_owner}/{settings.github_repo_layouts}.git"
    _ok(f"URL alvo: {layouts_url}")

    with tempfile.TemporaryDirectory() as tmpdir:
        env = svc._get_ssh_env()
        local_path = Path(tmpdir) / "layouts"

        print(f"  Clonando em diretório temporário: {local_path}")
        try:
            svc._get_or_clone_repo(layouts_url, local_path, env)
        except RuntimeError as e:
            _fail("Falha no git clone", str(e))
            print("  [AVISO] O repo 'layouts' nao existe ainda no GitHub ou o bot nao tem acesso.")
            print("          Crie o repositorio antes de usar o sistema em producao.")
            return False  # Aviso, nao erro fatal do SSH

        if not (local_path / ".git").exists():
            _fail("Clone não criou diretório .git — resultado inesperado")
            return False

        _ok(f"Clone bem-sucedido!")

        # Lista os templates disponíveis
        templates = [d for d in local_path.iterdir() if d.is_dir() and d.name != ".git"]
        if templates:
            _ok(f"Pastas encontradas no repo: {[t.name for t in templates]}")
        else:
            print("  [AVISO] Repo clonado mas sem pastas de template — verifique a estrutura do repo.")

    return True


# ---------------------------------------------------------------------------
# Teste 3: Deploy completo (clone + commit + push) em repo de teste
# ---------------------------------------------------------------------------

def test_deploy_completo(settings) -> bool:
    """
    Testa o fluxo de deploy: clona um repo, escreve um arquivo de teste,
    commita e faz push.

    Requer a variável SMOKE_DEPLOY_REPO no .env ou como variável de ambiente.
    Ex: SMOKE_DEPLOY_REPO=cyberflow-lat
    """
    _section("Teste 3: Deploy completo (clone -> commit -> push)")

    deploy_repo = settings.smoke_test_deploy_repo.strip()
    if not deploy_repo:
        print("  [PULAR] SMOKE_TEST_DEPLOY_REPO nao definido -- pulando teste de deploy.")
        print("       Para rodar: defina SMOKE_TEST_DEPLOY_REPO=nome-do-repo no .env.")
        return True  # Não é falha — é opcional

    _ok(f"Repo de deploy: {deploy_repo}")

    import time
    timestamp = int(time.time())
    test_file = f"smoke-test/{timestamp}.txt"
    test_content = f"Smoke test executado em {timestamp}. Pode deletar este arquivo."

    try:
        url = svc.deploy_lander_files(
            dest_repo_name=deploy_repo,
            files={test_file: test_content.encode("utf-8")},
            commit_message=f"smoke: teste de conexão SSH [{timestamp}]",
        )
        _ok(f"Deploy bem-sucedido! URL: {url}")
        print(f"  [INFO] Arquivo criado no repo: {test_file}")
        print(f"  [INFO] Pode deletar manualmente depois.")
        return True
    except Exception as e:
        _fail("Falha no deploy", str(e))
        return False


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------

def main() -> None:
    _header("LanderFlow — Smoke Test SSH")

    settings = get_settings()
    print(f"\n  Configurações carregadas:")
    print(f"    GITHUB_OWNER         = {settings.github_owner or '(vazio)'}")
    print(f"    GITHUB_REPO_LAYOUTS  = {settings.github_repo_layouts}")
    print(f"    DEPLOY_SSH_KEY_PATH  = {settings.deploy_ssh_key_path}")
    print(f"    DEPLOY_LOCAL_CLONE_DIR = {settings.deploy_local_clone_dir}")

    resultados = {}

    resultados["ssh_autenticacao"] = test_ssh_autenticacao(settings)

    # Só executa os próximos se a autenticação passou
    if resultados["ssh_autenticacao"]:
        resultados["clone_layouts"] = test_clone_layouts(settings)
        resultados["deploy_completo"] = test_deploy_completo(settings)
    else:
        print("\n  [PULAR] Testes 2 e 3 pulados (autenticacao falhou).")
        resultados["clone_layouts"] = False
        resultados["deploy_completo"] = False

    # Resumo final
    _header("Resultado Final")
    total = len(resultados)
    passou = sum(1 for v in resultados.values() if v)
    for nome, ok in resultados.items():
        status = "[OK]" if ok else "[FALHOU]"
        print(f"  {status}  {nome}")

    print(f"\n  {passou}/{total} testes passaram.")

    if passou < total:
        print("\n  [ATENCAO] Corrija os erros acima antes de fazer deploy em producao.")
        sys.exit(1)
    else:
        print("\n  [PRONTO] Ambiente SSH validado! Pronto para usar.")
        sys.exit(0)


if __name__ == "__main__":
    main()
