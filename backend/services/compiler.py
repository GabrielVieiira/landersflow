"""
Compilador de Landers — Motor Jinja2.

Responsabilidades:
1. Receber os dados brutos do payload + banco de dados
2. Converter vturb_delay de MM:SS para segundos inteiros
3. Construir os atributos de botão dinâmicos baseados no padrao_link_html
4. Montar o dicionário completo de placeholders (conforme Documentação de templates.md)
5. Renderizar os templates index e offer via Jinja2 (in-memory)

Todos os placeholders seguem RIGOROSAMENTE o dicionário da documentação.
"""

import re
from pathlib import Path
from typing import Optional

from jinja2 import Environment, StrictUndefined

from backend.models.plataforma import PlataformaCheckout
from backend.models.produto import Produto, ProdutoVariacao


# Diretório de scripts locais de checkout por slug de plataforma
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


def parse_vturb_delay(delay_str: str) -> int:
    """
    Converte o delay do VTurb de formato MM:SS para segundos inteiros.

    Regra documentada: (Minutos * 60) + Segundos
    Exemplos:
        "12:30" → 750
        "45:00" → 2700
        "00:30" → 30

    Args:
        delay_str: String no formato "MM:SS"

    Returns:
        Número inteiro de segundos

    Raises:
        ValueError: Se o formato não for válido
    """
    pattern = r"^\d{1,2}:\d{2}$"
    if not re.match(pattern, delay_str):
        raise ValueError(
            f"Formato de delay inválido: '{delay_str}'. Esperado: 'MM:SS' (ex: '12:30')"
        )

    parts = delay_str.split(":")
    minutes = int(parts[0])
    seconds = int(parts[1])

    if seconds >= 60:
        raise ValueError(f"Segundos inválidos: {seconds}. Deve ser entre 0 e 59.")

    return (minutes * 60) + seconds


def build_button_attrs(padrao_link_html: str, variacao: ProdutoVariacao) -> str:
    """
    Constrói o bloco completo de atributos do botão de checkout.

    O compilador NÃO injeta apenas a URL — ele monta o atributo inteiro
    baseado no padrão definido pela plataforma de checkout.

    Exemplos de padrao_link_html:
        - 'href="{url}"'                                  → href="https://checkout..."
        - 'href="#" data-click-path="/click/{qtd}"'       → href="#" data-click-path="/click/3"

    Args:
        padrao_link_html: Template do atributo (com {url} e/ou {qtd})
        variacao: Variação do produto com checkout_identifier e quantidade_potes

    Returns:
        String com os atributos HTML prontos para injeção no placeholder
    """
    return padrao_link_html.format(
        url=variacao.checkout_identifier,
        qtd=variacao.quantidade_potes,
        url_checkout=variacao.checkout_identifier,  # alias alternativo
    )


def load_checkout_script(slug_aplicacao: str) -> Optional[str]:
    """
    Lê o script de checkout local correspondente ao slug da plataforma.
    Se não encontrar, retorna None (o placeholder será apagado do HTML).

    Args:
        slug_aplicacao: Identificador da plataforma (ex: 'clickbank', 'generic')

    Returns:
        Conteúdo do script JS ou None se não houver script configurado
    """
    script_path = SCRIPTS_DIR / f"{slug_aplicacao}-tracker.js"
    if script_path.exists():
        return script_path.read_text(encoding="utf-8")
    return None


def build_index_context(
    plataforma: PlataformaCheckout,
    payload_data: dict,
) -> dict:
    """
    Monta o dicionário de contexto para renderização do template INDEX.

    Placeholders do arquivo index (conforme Documentação de templates.md §2.A):
        {{nome_produto}}        → Direto do payload
        {{headline}}            → Direto do payload
        {{pit_delay}}           → Convertido de MM:SS para segundos
        {{vturb_preload}}       → Direto do payload (tag <link> preload)
        {{vturb_script}}        → Direto do payload (embed do player)
        {{nome_arquivo_offer}}  → Nome do arquivo HTML de oferta
        {{checkout_script}}     → Script local do slug da plataforma (ou "" se inexistente)

    Args:
        plataforma: Modelo PlataformaCheckout do banco
        payload_data: Dados brutos do request do operador

    Returns:
        Dicionário pronto para Jinja2 Environment.render()
    """
    checkout_script = load_checkout_script(plataforma.slug_aplicacao) or ""
    pit_delay = parse_vturb_delay(payload_data["vturb_delay"])

    return {
        # --- Textos e Copy ---
        "nome_produto": payload_data["nome_produto"],
        "headline": payload_data["headline"],
        # A offer sempre fica em offer/index.html — caminho fixo, sem necessidade de payload
        "nome_arquivo_offer": "offer/",

        # --- Scripts de Vídeo (VTurb) ---
        "vturb_preload": payload_data.get("vturb_preload", ""),
        "vturb_script": payload_data.get("vturb_script", ""),

        # --- Delay VTurb (convertido para segundos inteiros) ---
        "pit_delay": pit_delay,

        # --- Script de Checkout (injetado ou removido) ---
        "checkout_script": checkout_script,
    }


def build_offer_context(
    produto: Produto,
    plataforma: PlataformaCheckout,
    variacoes: dict[int, ProdutoVariacao],
    payload_data: dict,
) -> dict:
    """
    Monta o dicionário de contexto para renderização do template OFFER.

    Placeholders do arquivo offer (conforme Documentação de templates.md §2.B e §2.C):
        {{nome_produto}}          → Direto do payload
        {{cor_primaria}}          → Hash HEX do banco (cor do card)
        {{cor_secundaria}}        → Hash HEX do banco (cor do botão)
        {{cor_background}}        → Hash HEX do banco (cor de fonte)
        {{img_pote_2}}            → URL da imagem da variação de 2 potes
        {{img_pote_3}}            → URL da imagem da variação de 3 potes
        {{img_pote_6}}            → URL da imagem da variação de 6 potes
        {{attr_botao_2_potes}}    → Atributos construídos do botão de 2 potes
        {{attr_botao_3_potes}}    → Atributos construídos do botão de 3 potes
        {{attr_botao_6_potes}}    → Atributos construídos do botão de 6 potes
        {{track_checkout}}        → Script de tracking final (ou "" se inexistente)

    Args:
        produto: Modelo Produto do banco
        plataforma: Modelo PlataformaCheckout do banco
        variacoes: Dict {quantidade_potes: ProdutoVariacao}
        payload_data: Dados brutos do request do operador

    Returns:
        Dicionário pronto para Jinja2 Environment.render()
    """
    track_script = load_checkout_script(f"{plataforma.slug_aplicacao}-track") or ""

    def _get_variacao_attr(qtd: int) -> str:
        """Retorna os atributos do botão se a variação existir, senão string vazia."""
        if qtd not in variacoes:
            return ""
        return build_button_attrs(plataforma.padrao_link_html, variacoes[qtd])

    def _get_variacao_imagem(qtd: int) -> str:
        """Retorna a URL da imagem se a variação existir, senão string vazia."""
        if qtd not in variacoes:
            return ""
        return variacoes[qtd].url_imagem

    return {
        # --- Texto ---
        "nome_produto": payload_data["nome_produto"],

        # --- Cores CSS Variables (injetadas no :root) ---
        "cor_primaria": produto.cor_primaria,
        "cor_secundaria": produto.cor_secundaria,
        "cor_background": produto.cor_background,

        # --- Imagens das Variações (dinâmicas, sem hardcode) ---
        "img_pote_1": _get_variacao_imagem(1),
        "img_pote_2": _get_variacao_imagem(2),
        "img_pote_3": _get_variacao_imagem(3),
        "img_pote_6": _get_variacao_imagem(6),

        # --- Atributos de Botão (bloco completo, dinâmico) ---
        "attr_botao_1_pote":  _get_variacao_attr(1),
        "attr_botao_2_potes": _get_variacao_attr(2),
        "attr_botao_3_potes": _get_variacao_attr(3),
        "attr_botao_6_potes": _get_variacao_attr(6),

        # --- Script de Tracking (ou string vazia para limpeza) ---
        "track_checkout": track_script,
    }


def render_template(template_content: str, context: dict) -> str:
    """
    Renderiza um template HTML via Jinja2 com substituição determinística.

    Usa StrictUndefined para detectar placeholders faltantes durante o desenvolvimento.
    Em produção, use Undefined para silenciar erros de chaves não encontradas
    e manter o HTML limpo (sem tags {{...}} vazias).

    Args:
        template_content: Conteúdo bruto do arquivo HTML
        context: Dicionário de placeholders e seus valores

    Returns:
        HTML final compilado com todos os placeholders substituídos

    Raises:
        jinja2.UndefinedError: Se um placeholder do template não estiver no contexto
    """
    env = Environment(
        undefined=StrictUndefined,
        autoescape=False,    # HTML não deve ser escapado (injetamos scripts e atributos raw)
        keep_trailing_newline=True,
    )
    tmpl = env.from_string(template_content)
    return tmpl.render(**context)


def compile_lander_pages(
    lander_slug: str,
    index_template_files: dict[str, bytes],
    offer_template_files: dict[str, bytes],
    produto: Produto,
    plataforma: PlataformaCheckout,
    variacoes: dict[int, ProdutoVariacao],
    payload_data: dict,
) -> dict[str, bytes | str]:
    """
    Ponto de entrada principal do compilador.
    Processa os templates (index + offer) e monta o dict final pronto para deploy.

    Estrutura de entrada (do repo 'layouts'):
        index_template_files: {'index.html': b'...', 'style.css': b'...', 'assets/logo.png': b'...'}
        offer_template_files: {'offer.html': b'...', 'style.css': b'...'}

    Estrutura de saida (pronta para o repo de destino):
        {
            '{slug}/index.html':          str  <- compilado pelo Jinja2
            '{slug}/style.css':           bytes <- copiado sem modificacao
            '{slug}/script.js':           bytes <- copiado sem modificacao
            '{slug}/assets/logo.png':     bytes <- copiado sem modificacao
            '{slug}/offer/index.html':    str  <- offer.html compilado e renomeado
            '{slug}/offer/style.css':     bytes <- copiado sem modificacao
        }

    Regras de montagem:
        - Arquivos do index template vao para  '{slug}/'
        - Arquivos do offer template vao para  '{slug}/offer/'
        - 'offer.html' e renomeado para 'index.html' dentro de offer/
        - Apenas .html passa pelo Jinja2; demais arquivos passam como bytes

    Args:
        lander_slug:          Slug/ID da lander (nome da pasta no repo de destino)
        index_template_files: Todos os arquivos do template index (bytes)
        offer_template_files: Todos os arquivos do template offer (bytes)
        produto:              Modelo Produto com cores
        plataforma:           Modelo PlataformaCheckout com slug e padrao de botao
        variacoes:            Dict {quantidade_potes: ProdutoVariacao}
        payload_data:         Dados brutos do payload de compilacao

    Returns:
        Dict {caminho_no_repo_destino: conteudo (str para HTML, bytes para binarios)}
    """
    index_context = build_index_context(plataforma, payload_data)
    offer_context = build_offer_context(produto, plataforma, variacoes, payload_data)

    output: dict[str, bytes | str] = {}

    # --- Arquivos do template INDEX → raiz do slug ---
    for filename, content in index_template_files.items():
        dest_path = f"{lander_slug}/{filename}"
        if filename.endswith(".html"):
            # So HTMLs passam pelo compilador Jinja2
            html_str = content.decode("utf-8")
            output[dest_path] = render_template(html_str, index_context)
        else:
            # CSS, JS, imagens e outros assets: copia direta
            output[dest_path] = content

    # --- Arquivos do template OFFER → subpasta offer/ ---
    for filename, content in offer_template_files.items():
        # 'offer.html' e renomeado para 'index.html' dentro da subpasta offer/
        dest_filename = "index.html" if filename == "offer.html" else filename
        dest_path = f"{lander_slug}/offer/{dest_filename}"
        if filename.endswith(".html"):
            html_str = content.decode("utf-8")
            output[dest_path] = render_template(html_str, offer_context)
        else:
            output[dest_path] = content

    return output
