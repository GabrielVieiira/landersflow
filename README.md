# LanderFlow

Sistema de automação para criação e deploy de Landing Pages via GitHub Pages com integração ao RedTrack.

## Pré-requisitos

- Python 3.11+
- Poetry (ou pip)

## Instalação

```bash
# Copie e configure o .env
cp .env.example .env

# Instale as dependências
poetry install
# OU via pip diretamente:
pip install fastapi uvicorn[standard] sqlmodel aiosqlite httpx PyGithub jinja2 pydantic-settings python-dotenv streamlit requests python-multipart
```

## Configuração

Edite o arquivo `.env` com suas credenciais:

```
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=seu-usuario
REDTRACK_API_KEY=...
```

## Execução

**Terminal 1 — Backend FastAPI:**
```bash
# Com Poetry:
poetry run uvicorn backend.main:app --reload --port 8000

# Com Python direto:
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend Streamlit:**
```bash
# Com Poetry:
poetry run streamlit run frontend/app.py

# Com Python direto:
python -m streamlit run frontend/app.py
```

- **API Swagger:** http://localhost:8000/docs
- **Frontend Admin:** http://localhost:8501

## Estrutura

```
landersflow/
├── pyproject.toml
├── .env.example
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (pydantic-settings)
│   ├── database.py          # SQLite async engine
│   ├── models/              # SQLModel 3FN
│   │   ├── plataforma.py    # Nicho, PlataformaCheckout
│   │   ├── produto.py       # Produto, Variacao, CheckoutParam (EAV)
│   │   ├── template.py      # Template
│   │   ├── dominio.py       # Dominio
│   │   ├── lander.py        # Lander
│   │   ├── traffic.py       # TrafficChannel, Postback
│   │   └── campanha.py      # Campanha
│   ├── routes/              # FastAPI routers
│   │   ├── landers.py       # POST /compile, POST /deploy/{id}
│   │   ├── produtos.py      # CRUD produtos
│   │   ├── templates.py     # CRUD templates
│   │   └── campanhas.py     # POST campanhas (RedTrack)
│   ├── services/
│   │   ├── compiler.py      # Motor Jinja2 + regras de negócio
│   │   ├── github_service.py    # PyGithub (in-memory)
│   │   ├── redtrack_service.py  # httpx async
│   │   └── cloudflare_service.py # httpx async
│   └── scripts/
│       ├── clickbank-tracker.js
│       └── generic-tracker.js
└── frontend/
    └── app.py               # Streamlit UI
```

## Fluxo de Uso

1. **Cadastre** um Produto com suas variações (2, 3, 6 potes) e cores HEX
2. **Cadastre** Templates apontando para arquivos no GitHub
3. **Compile** uma Lander pelo formulário Streamlit (preview HTML para QA)
4. **Deploy** após aprovação → commit no GitHub Pages + polling + RedTrack
5. **Crie** a Campanha no RedTrack vinculando Traffic Channel e postbacks S2S
