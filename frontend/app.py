"""
LanderFlow — Interface Administrativa (Streamlit)

Fluxo de navegação:
    1. Sidebar → Status da API e configurações
    2. Página "Nova Lander" → Formulário de compilação
    3. Preview HTML após compilação (QA visual)
    4. Botão "Deploy" → Aciona o pipeline no backend
    5. Painel "Minhas Landers" → Histórico e status
    6. Página "Nova Campanha" → Vincula Lander + Traffic Channel no RedTrack
"""

import time
from typing import Optional

import requests
import streamlit as st

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="LanderFlow",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000/api/v1"


# =============================================================================
# HELPERS DE API
# =============================================================================

def api_get(endpoint: str) -> Optional[dict | list]:
    """GET request para o backend FastAPI."""
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend offline. Inicie com: `uvicorn backend.main:app --reload`")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro da API: {e.response.json().get('detail', str(e))}")
        return None


def api_post(endpoint: str, payload: dict) -> Optional[dict]:
    """POST request para o backend FastAPI."""
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend offline. Inicie com: `uvicorn backend.main:app --reload`")
        return None
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e))
        st.error(f"Erro da API [{e.response.status_code}]: {detail}")
        return None


def check_api_health() -> bool:
    """Verifica se o backend está respondendo."""
    try:
        r = requests.get("http://localhost:8000/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.image(
        "https://via.placeholder.com/200x60/1a1a2e/ffffff?text=LanderFlow",
        use_column_width=True,
    )
    st.markdown("---")

    # Status da API
    api_online = check_api_health()
    if api_online:
        st.success("🟢 Backend Online")
    else:
        st.error("🔴 Backend Offline")
        st.code("uvicorn backend.main:app --reload", language="bash")

    st.markdown("---")

    # Navegação
    pagina = st.radio(
        "Navegação",
        options=["🚀 Nova Lander", "📋 Minhas Landers", "📣 Nova Campanha", "⚙️ Configurações"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("LanderFlow v0.1.0")
    st.caption("[Documentação da API](http://localhost:8000/docs)")


# =============================================================================
# PÁGINA: NOVA LANDER
# =============================================================================

if pagina == "🚀 Nova Lander":
    st.title("🚀 Compilar Nova Lander")
    st.markdown(
        "Preencha os dados abaixo. O sistema irá compilar os templates, "
        "substituir todos os placeholders e gerar o HTML para revisão visual antes do deploy."
    )

    # Carrega opções do backend
    produtos_data = api_get("/produtos") or []
    templates_data = api_get("/templates") or []

    produtos_options = {p["nome"]: p["id"] for p in produtos_data}
    templates_index = {t["nome"]: t["id"] for t in templates_data if t["tipo_template_id"] == 1}
    templates_offer = {t["nome"]: t["id"] for t in templates_data if t["tipo_template_id"] == 2}

    with st.form("form_nova_lander", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📦 Produto e Templates")
            produto_nome = st.selectbox(
                "Produto",
                options=list(produtos_options.keys()),
                help="Produto cadastrado no sistema (define cores, variações e plataforma de checkout)",
            )
            produto_id = produtos_options.get(produto_nome, 0)

            template_index_nome = st.selectbox(
                "Template Index (VSL Principal)",
                options=list(templates_index.keys()),
                help="Template da página principal com o vídeo de vendas",
            )
            template_index_id = templates_index.get(template_index_nome, 0)

            template_offer_nome = st.selectbox(
                "Template Offer (Cards de Checkout)",
                options=list(templates_offer.keys()),
                help="Template da página de ofertas (potes de produto)",
            )
            template_offer_id = templates_offer.get(template_offer_nome, 0)

            nome_arquivo_offer = st.text_input(
                "Nome do arquivo de oferta",
                value="offer.html",
                help="Nome do arquivo HTML gerado para a oferta (ex: offer-checkout.html)",
            )

        with col2:
            st.subheader("✍️ Copy e Configurações")

            headline = st.text_area(
                "Headline Principal",
                placeholder="A promessa mais matadora do seu produto...",
                height=100,
                help="Injetada no placeholder {{headline}} do template index",
            )

            nome_produto = st.text_input(
                "Nome do Produto (para exibição)",
                placeholder="ex: Gelatide",
                help="Injetado no placeholder {{nome_produto}} em ambos os templates",
            )

        st.subheader("🎬 Configurações do VTurb")
        col3, col4 = st.columns([1, 2])

        with col3:
            vturb_delay = st.text_input(
                "Delay do VTurb (MM:SS)",
                value="12:30",
                help="Tempo para revelar os botões de checkout. Convertido para segundos (ex: '12:30' → 750s)",
            )

        with col4:
            vturb_preload = st.text_area(
                "VTurb Preload (tag <link>)",
                placeholder="<link rel='preload' href='...' as='script'>",
                height=68,
                help="Tag de preload DNS fornecida pelo VTurb. Injetada no <head>.",
            )

        vturb_script = st.text_area(
            "VTurb Script Embed",
            placeholder="<script src='...'></script> ou <vturb-smartplayer ...></vturb-smartplayer>",
            height=100,
            help="Script principal do player VTurb. Injetado no placeholder {{vturb_script}}.",
        )

        st.subheader("🌐 Infraestrutura de Deploy")
        col5, col6 = st.columns(2)

        with col5:
            nicho_id = st.number_input("ID do Nicho", min_value=1, value=1, step=1)
        with col6:
            dominio_id = st.number_input("ID do Domínio", min_value=1, value=1, step=1)

        st.markdown("---")
        submitted = st.form_submit_button(
            "🔨 Compilar Lander",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not produto_id or not template_index_id or not template_offer_id:
            st.warning("⚠️ Selecione Produto e Templates antes de compilar.")
        elif not headline:
            st.warning("⚠️ A Headline é obrigatória.")
        elif not nome_produto:
            st.warning("⚠️ Informe o Nome do Produto para exibição.")
        else:
            payload = {
                "produto_id": produto_id,
                "template_index_id": template_index_id,
                "template_offer_id": template_offer_id,
                "nome_produto": nome_produto,
                "nome_arquivo_offer": nome_arquivo_offer,
                "headline": headline,
                "vturb_preload": vturb_preload,
                "vturb_script": vturb_script,
                "vturb_delay": vturb_delay,
                "nicho_id": int(nicho_id),
                "dominio_id": int(dominio_id),
            }

            with st.spinner("Compilando templates..."):
                result = api_post("/landers/compile", payload)

            if result:
                st.session_state["compiled_lander"] = result
                st.success(
                    f"✅ Lander **#{result['lander_id']}** compilada! "
                    f"Delay configurado: **{result['vturb_delay_segundos']} segundos**"
                )

    # ==========================================================================
    # PREVIEW E DEPLOY (após compilação)
    # ==========================================================================

    if "compiled_lander" in st.session_state:
        result = st.session_state["compiled_lander"]
        st.markdown("---")
        st.subheader("👁️ Preview para QA Visual")

        tab_index, tab_offer, tab_deploy = st.tabs(
            ["📄 index.html", "🛒 offer.html", "🚀 Deploy"]
        )

        with tab_index:
            st.markdown("**Revise o HTML abaixo antes de fazer o deploy:**")
            st.code(result["html_index_preview"], language="html")
            st.download_button(
                "⬇️ Baixar index.html",
                data=result["html_index_preview"],
                file_name="index.html",
                mime="text/html",
            )

        with tab_offer:
            st.markdown("**Revise o HTML da oferta (cards de potes):**")
            st.code(result["html_offer_preview"], language="html")
            st.download_button(
                "⬇️ Baixar offer.html",
                data=result["html_offer_preview"],
                file_name="offer.html",
                mime="text/html",
            )

        with tab_deploy:
            st.markdown(
                f"**Lander ID:** `#{result['lander_id']}`  \n"
                f"**Delay VTurb:** `{result['vturb_delay_segundos']} segundos`"
            )
            st.warning(
                "⚠️ Após o deploy, o sistema irá:\n"
                "1. Commitar os arquivos no GitHub Pages\n"
                "2. Aguardar a URL ficar ativa (polling até 5 min)\n"
                "3. Registrar automaticamente no RedTrack"
            )

            if st.button(
                f"🚀 Confirmar Deploy da Lander #{result['lander_id']}",
                type="primary",
                use_container_width=True,
            ):
                with st.spinner("Iniciando deploy em background..."):
                    deploy_result = api_post(
                        f"/landers/deploy/{result['lander_id']}", {}
                    )

                if deploy_result:
                    st.success(
                        f"🎯 Deploy iniciado! Status: `{deploy_result['status']}`\n\n"
                        f"{deploy_result['message']}"
                    )
                    del st.session_state["compiled_lander"]


# =============================================================================
# PÁGINA: MINHAS LANDERS
# =============================================================================

elif pagina == "📋 Minhas Landers":
    st.title("📋 Minhas Landers")

    if st.button("🔄 Atualizar"):
        st.rerun()

    landers_data = api_get("/landers") or []

    if not landers_data:
        st.info("Nenhuma lander cadastrada ainda. Crie a primeira em '🚀 Nova Lander'.")
    else:
        for lander in landers_data:
            with st.expander(
                f"#{lander['id']} — {lander['produto_nome']} | "
                f"{'🟢 Live' if lander.get('url_final') and lander.get('redtrack_lander_id') else '🟡 Pendente'}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Headline:** {lander['headline']}")
                    st.markdown(f"**Delay VTurb:** {lander['vturb_delay_segundos']}s")
                with col2:
                    if lander.get("url_final"):
                        st.markdown(f"**URL:** [{lander['url_final']}]({lander['url_final']})")
                    if lander.get("redtrack_lander_id"):
                        st.markdown(f"**RedTrack ID:** `{lander['redtrack_lander_id']}`")

                # Status detalhado em tempo real
                status_data = api_get(f"/landers/{lander['id']}")
                if status_data:
                    status_color = {
                        "live": "🟢",
                        "deploying": "🟡",
                        "pending": "⚪",
                        "error": "🔴",
                    }.get(status_data["status"], "⚪")
                    st.caption(f"{status_color} {status_data['message']}")


# =============================================================================
# PÁGINA: NOVA CAMPANHA
# =============================================================================

elif pagina == "📣 Nova Campanha":
    st.title("📣 Criar Nova Campanha no RedTrack")
    st.markdown(
        "Vincula uma Lander deployada a um Traffic Channel e cria a campanha "
        "completa no RedTrack com postbacks S2S configurados."
    )

    landers_data = api_get("/landers") or []
    landers_live = [l for l in landers_data if l.get("redtrack_lander_id")]

    if not landers_live:
        st.warning(
            "⚠️ Nenhuma Lander deployada e registrada no RedTrack. "
            "Faça o deploy de uma lander primeiro."
        )
    else:
        landers_options = {
            f"#{l['id']} — {l['produto_nome']}": l["id"] for l in landers_live
        }

        with st.form("form_nova_campanha"):
            st.subheader("Dados da Campanha")

            nome_campanha = st.text_input(
                "Nome da Campanha",
                placeholder="ex: Gelatide — Taboola BR Q2 2025",
            )

            lander_selecionada = st.selectbox(
                "Lander (deployada)",
                options=list(landers_options.keys()),
            )
            lander_id = landers_options.get(lander_selecionada, 0)

            traffic_channel = st.text_input(
                "Traffic Channel",
                placeholder="ex: Taboola, Outbrain, Meta Ads",
                help="Se não existir, será criado automaticamente no RedTrack.",
            )

            st.markdown("---")
            st.subheader("Configurações Avançadas (Opcional)")

            postback_url = st.text_input(
                "URL de Postback S2S",
                placeholder="https://tracker.plataforma.com/postback?...",
            )

            prelander_id = st.text_input(
                "ID da Pre-Lander no RedTrack",
                placeholder="ex: 12345",
            )

            submitted = st.form_submit_button(
                "📣 Criar Campanha no RedTrack",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not nome_campanha or not traffic_channel or not lander_id:
                st.warning("⚠️ Preencha Nome da Campanha, Traffic Channel e Lander.")
            else:
                payload = {
                    "nome": nome_campanha,
                    "traffic_channel_nome": traffic_channel,
                    "lander_id": lander_id,
                    "postback_url": postback_url or None,
                    "prelander_redtrack_id": prelander_id or None,
                }

                with st.spinner("Criando campanha no RedTrack..."):
                    result = api_post("/campanhas", payload)

                if result:
                    st.success("✅ Campanha criada com sucesso!")
                    st.info(f"**RedTrack Campaign ID:** `{result['redtrack_campaign_id']}`")
                    if result.get("url_cloaker"):
                        st.success(f"🔗 **URL para o Cloaker:**")
                        st.code(result["url_cloaker"])


# =============================================================================
# PÁGINA: CONFIGURAÇÕES
# =============================================================================

elif pagina == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    st.markdown("Verifique as variáveis de ambiente e o status dos serviços externos.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔗 Serviços")
        st.markdown("**Backend FastAPI:**")
        if check_api_health():
            st.success("🟢 Online — http://localhost:8000")
        else:
            st.error("🔴 Offline")

        st.markdown("**Documentação Swagger:**")
        st.markdown("[Abrir /docs](http://localhost:8000/docs)")

    with col2:
        st.subheader("📋 Variáveis de Ambiente")
        st.info(
            "Configure o arquivo `.env` na raiz do projeto seguindo o `.env.example`.\n\n"
            "**Blocos obrigatórios:**\n"
            "- `GITHUB_TOKEN` e `GITHUB_OWNER`\n"
            "- `REDTRACK_API_KEY`\n"
            "- `DATABASE_URL` (padrão SQLite já configurado)\n"
            "- `NICHOS_PERMITIDOS` (ex: WL,TT,MM)"
        )

    st.markdown("---")
    st.subheader("🚀 Comandos de Inicialização")
    st.code(
        "# Instalar dependências\npoetry install\n\n"
        "# Iniciar backend (terminal 1)\npoetry run uvicorn backend.main:app --reload --port 8000\n\n"
        "# Iniciar frontend (terminal 2)\npoetry run streamlit run frontend/app.py",
        language="bash",
    )
