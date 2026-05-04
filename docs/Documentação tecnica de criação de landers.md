# Documentação Técnica: Automação e Criação de Landers ("Back-end")

## 1. Estrutura de Entrada (Payload da Demanda)
Quando o operador preenche o formulário no sistema, o "Front-end" deve enviar um JSON padronizado para a Automação. Este é o contrato de dados de entrada que iniciará o processo de compilação:

```json
{
  "produto_id": 123,
  "template_index_id": 45,
  "template_offer_id": 46,
  "nome_produto": "Gelatide",
  "headline": "A promessa matadora...",
  "vturb_preload": "<link rel='preload'...>",
  "vturb_script": "<script>...</script>",
  "vturb_delay": "12:30",
  "nicho_id": 2,
  "dominio_id": 7
}
```

> **Nota:** O campo `nome_arquivo_offer` foi **removido** do payload. O arquivo de oferta é sempre
> servido em `offer/index.html` — caminho fixo definido pelo compilador, sem intervenção do operador.

---

## 2. Padrão de Arquitetura e Tratamento de Placeholders

A Automação atua como um "Compilador". Ela faz o download de **toda a pasta** do template (index ou offer) do repositório `layouts` e realiza o *Find & Replace* rigoroso das chaves duplas `{{chave}}` **apenas nos arquivos `.html`**. Os demais arquivos (CSS, JS, imagens, fontes) são copiados como bytes sem modificação.

Abaixo está a documentação de como o back-end deve se comportar para processar e atualizar cada tipo de placeholder:

### A. Substituição Direta (Textos e Imagens)
O back-end apenas pega o valor do payload ou do banco e substitui em texto plano.
* `{{nome_produto}}` → Substituído pelo valor do payload.
* `{{headline}}` → Substituído pelo valor do payload.
* `{{nome_arquivo_offer}}` → **Fixo em `offer/`** — o compilador injeta automaticamente, o operador não precisa informar.
* `{{vturb_preload}}` e `{{vturb_script}}` → Substituído pelos scripts crus enviados no payload.
* `{{img_pote_2}}`, `{{img_pote_3}}`, `{{img_pote_6}}` → O back-end busca na tabela `PRODUTO_VARIACAO` as URLs das imagens baseadas no ID do produto e injeta nas chaves correspondentes.

### B. Substituição de Cores (CSS Variables)
O back-end consulta a tabela `PRODUTO` e busca as chaves HEX das cores, substituindo no `<head>` do arquivo `offer.html`:
* `{{cor_primaria}}`, `{{cor_secundaria}}`, `{{cor_background}}` → Substituídos pelos respectivos Hashes HEX (ex: `#FF5733`).

### C. Geração de Botões Dinâmicos (Atributos de Ação)
O back-end **não injeta apenas a URL**. Ele constrói o bloco inteiro de atributos baseando-se nas regras da plataforma.
* **Placeholders:** `{{attr_botao_2_potes}}`, `{{attr_botao_3_potes}}`, `{{attr_botao_6_potes}}`.
* **Comportamento do Back-end:** 1. Lê a coluna `padrao_link_html` da tabela `PLATAFORMA_CHECKOUT` (Ex: `href="#" data-click-path="/click/{qtd}"` ou `href="{url_checkout}"`).
    2. Lê a tabela `PRODUTO_VARIACAO` para pegar as informações daquele pote.
    3. Constrói a string final (Ex: `href="#" data-click-path="/click/3"`) e injeta no placeholder.

### D. Injeção Dinâmica de Scripts
* **Placeholders:** `{{checkout_script}}` (no index) e `{{track_checkout}}` (na offer).
* **Comportamento do Back-end:** Verifica na tabela da plataforma se há scripts obrigatórios para aquela oferta (ex: pixel, script de clique do RedTrack). Se houver, injeta o script inteiro. Se não houver, **o back-end deve apagar a tag `{{chave}}`** do HTML para evitar vazamento de código sujo no front-end.

---

## 3. Regras de Negócio de Processamento ("Back-end")

A automação executará lógicas matemáticas e estruturais cruzando os dados do formulário com as regras do banco de dados antes de iniciar o deploy.

### Regra 1: Tratamento do Delay do Vturb
O sistema deve ler a string `vturb_delay` (ex: "12:30" ou "45:00") que vem do payload, realizar a conversão matemática estrita `(Minutos * 60) + Segundos` (ex: `750` segundos) e injetar esse número inteiro na variável `{{pit_delay}}`.

### Regra 2: Roteamento de Checkouts (Fim das URLs Hardcoded)
O back-end agora é guiado 100% pela tabela de `PLATAFORMA_CHECKOUT`. 
* Em vez de tentar "adivinhar" se é ClickBank ou Genérica via *If/Else* hardcoded, o código consulta a plataforma atrelada ao produto.
* Se a plataforma exige variáveis personalizadas (ex: o `vendor` do ClickBank), o back-end busca na tabela `PRODUTO_CHECKOUT_PARAM` e as inclui dinamicamente no script que será injetado nos placeholders de tracking.

---

## 4. Repositório de Templates (`layouts`) e Estrutura de Arquivos

### 4.1. Organização do Repositório Fonte (`layouts`)

O repositório `layouts` é a **fonte de verdade** de todos os templates. É somente-leitura para o sistema de deploy. Sua estrutura interna:

```
layouts/
├── lander/
│   ├── cnn/
│   │   ├── index.html    ← Placeholders {{headline}}, {{vturb_script}} etc.
│   │   ├── style.css
│   │   ├── script.js
│   │   └── assets/
│   └── [outros templates]/
│
└── offer_section/
    ├── padrao/
    │   ├── offer.html    ← Placeholders {{attr_botao_X}}, {{cor_primaria}} etc.
    │   ├── style.css
    │   └── assets/
    └── [outros templates]/
```

O campo `Template.repo_github` armazena o **caminho da pasta** dentro desse repositório:
- Template lander  → `"lander/cnn"`
- Template offer   → `"offer_section/padrao"`

### 4.2. Estrutura no Repositório de Destino (Nicho)

Após o deploy, cada lander ocupa uma pasta isolada no repositório do nicho correspondente:

```
[niche-repo]/
└── lander-{id}/
    ├── index.html        ← compilado com Jinja2
    ├── style.css         ← copiado como bytes (sem modificação)
    ├── script.js         ← copiado como bytes
    ├── assets/           ← assets do index (copiados como bytes)
    └── offer/
        ├── index.html    ← offer.html compilado + renomeado
        └── style.css     ← assets do offer (copiados como bytes)
```

**Regras de montagem aplicadas pelo compilador:**
- Arquivos do template `index` → raiz de `lander-{id}/`
- Arquivos do template `offer` → sub-pasta `lander-{id}/offer/`
- `offer.html` é **renomeado** para `offer/index.html` automaticamente
- Somente arquivos `.html` passam pelo motor Jinja2; demais são bytes puros

---

## 5. Integração de Deploy e RedTrack (Pós-Montagem)

Após a Automação compilar as páginas e a revisão humana (QA) aprovar, o sistema segue o fluxo de publicação.

### A. Deploy via Git SSH

O sistema utiliza Git nativo com autenticação SSH (chave ED25519 `deploy_bot`) para publicar os arquivos.

**Fluxo:**
1. Clona o repositório do nicho localmente (ou faz `git pull` se já existir)
2. Escreve todos os arquivos compilados na pasta `lander-{id}/`
3. Configura a identidade do bot (`git config user.name/email`)
4. Verifica se há mudanças reais (`git status --porcelain`)
5. Executa: `git add .` → `git commit -m "feat: deploy lander #N"` → `git push`

Cada nicho tem um repositório de destino próprio. O `Dominio.url` (ex: `echozen.com`) determina o nome do repositório (`echozen-com`).

### B. Registro no RedTrack (API)
Após a confirmação do deploy, a automação fará a chamada final para gerar a "Lander ID" na plataforma de rastreio.

**Payload Final (Gerado automaticamente pela Automação):**

```json
{
  "name": "Nome formatado da Lander", 
  "url": "https://dominiodonicho.com/lander-7/",
  "tracking_domain": "dominiodonicho.com",
  
  // LÓGICA CONDICIONAL DE ROTEAMENTO DE LISTICLE:
  // O back-end lê a coluna 'integra_redtrack_offer' da tabela PLATAFORMA_CHECKOUT
  // Se a plataforma usar links diretos (integração externa): "listicle": true
  // Se a plataforma depender do RedTrack para rotear (ex: Clickbank via ID): "listicle": false
}
```