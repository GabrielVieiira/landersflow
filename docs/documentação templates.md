# Documentação Técnica: Padronização de Templates Front-End (Landers e Offers)

## 1. Visão Geral e Arquitetura Agnóstica
Esta documentação define o padrão rigoroso para a criação de templates de landers em HTML/CSS (Páginas de Vendas). 

O princípio central desta arquitetura é o **Template Agnóstico**. O repositório front-end atua estritamente como a camada visual (Single Source of Truth para o design). Os templates **não devem conter** links de checkout chumbados (hardcoded), scripts de rastreamento específicos de plataformas de pagamento, nome do produto hardcoded, etc. 

Toda a inteligência de links e scripts é injetada dinamicamente pela Automação de Deploy no momento da compilação, utilizando o sistema de "Placeholders" (Chaves Duplas `{{chave}}`).

---

## 2. Dicionário de Placeholders Universais

A Automação varre o código-fonte buscando as chaves exatas abaixo. A nomenclatura deve ser respeitada rigorosamente, observando em qual arquivo cada chave deve ser utilizada.

### A. Textos, Copy e Scripts de Vídeo (HTML)
| Placeholder | Arquivo Alvo | Descrição |
| :--- | :--- | :--- |
| `{{nome_produto}}` | Ambos | Nome oficial do produto. |
| `{{headline}}` | `index` | A promessa principal (Headline). |
| `{{pit_delay}}` | `index` | Tempo em segundos para exibição de botões (delay do Vturb). |
| `{{vturb_preload}}` | `index` | Tag de pre-load de DNS/Recursos informada pelo operador para otimizar o carregamento do Vturb no `<head>`. |
| `{{vturb_script}}` | `index` | Script principal de embed do Vturb informado pelo operador, posicionado onde o vídeo deve renderizar. |
| `{{nome_arquivo_offer}}` | `index` | Caminho para a página de oferta. **Valor fixo: `"offer/"`** — injetado automaticamente pelo compilador; o template deve usar `src="{{nome_arquivo_offer}}"`no iframe. |

### B. Mídias e Imagens (Apenas arquivo `offer`)
As imagens dinâmicas devem receber o placeholder diretamente no atributo `src`. O restante das imagens estruturais do layout permanece fixo no repositório.

| Placeholder | Descrição | Exemplo de Uso no HTML |
| :--- | :--- | :--- |
| `{{img_pote_2}}` | Caminho/URL da imagem para 2 unidades. | `<img src="{{img_pote_2}}" alt="2 Potes">` |
| `{{img_pote_3}}` | Caminho/URL da imagem para 3 unidades. | `<img src="{{img_pote_3}}" alt="3 Potes">` |
| `{{img_pote_6}}` | Caminho/URL da imagem para 6 unidades. | `<img src="{{img_pote_6}}" alt="6 Potes">` |

### C. Cores e Temas (Restrito ao arquivo `offer`)
**Regra Crítica:** A injeção de CSS dinâmico acontece **exclusivamente no arquivo de oferta (`offer`)**. O layout geral da página é padrão. As únicas variáveis de design que a automação irá alterar correspondem à área de checkout: cores dos cards dos produtos, botões dos cards e fontes dos cards.

O mapeamento de cores deve ser feito obrigatoriamente utilizando CSS Variables (`var()`) declaradas no `:root` dentro de uma tag `<style>` no `<head>` do documento. 

```html
<style>
  :root {
    --cor-card-fundo: {{cor_primaria}};
    --cor-card-botao: {{cor_secundaria}};
    --cor-card-fonte: {{cor_background}}; 
  }
  
  .card-produto { background-color: var(--cor-card-fundo); color: var(--cor-card-fonte); }
  .card-produto .btn-comprar { background-color: var(--cor-card-botao); }
</style>
```

---

## 3. O Padrão de Botões de Checkout (Atributos Dinâmicos)

É terminantemente proibido inserir atributos como `href="..."`, `target="..."`, `onclick="..."` ou `data-click-path="..."` nativamente nas tags de link (`<a>`) ou botões (`<button>`) que levam ao checkout.

A plataforma de pagamento dita como o botão deve se comportar. Portanto, o template da `offer` deve receber um placeholder que representa **o bloco inteiro de atributos**.

### Placeholders de Ação:
* `{{attr_botao_2_potes}}`
* `{{attr_botao_3_potes}}`
* `{{attr_botao_6_potes}}`

### Como escrever no Template (`offer`):
```html
    <img class="pote" src="{{img_pote_3}}" alt="3 bottles>
```
```html
    <a class="btn" {{attr_botao_3_potes}}>BUY NOW</a>
```

---

## 4. Injeção de Scripts de Plataforma e Rastreamento

A arquitetura de rastreamento é dividida entre scripts nativos (padrão da infraestrutura) e scripts dinâmicos injetados via automação, dependendo da plataforma de pagamento ou rede de tráfego selecionada.

### 4.1. Regras de Distribuição de Scripts

Abaixo está o mapeamento exato de onde cada script nativo ou placeholder de injeção deve ser posicionado dentro da estrutura HTML dos templates:

| Elemento / Placeholder | Arquivo Alvo | Localização | Descrição |
| :--- | :--- | :--- | :--- |
| **Tracking Script Nativo** | `index.html` | Dentro do `<head>` | Script padrão e obrigatório (hardcoded no template) para rastreamento de visitas e resolução do domínio raiz. |
| `{{checkout_script}}` | `index.html` | Final do `<head>` | Injeção dinâmica de scripts adicionais exigidos por plataformas específicas (ex: pixel, verificação de domínio). |
| `{{track_checkout}}` | `offer.html` | Final do `<body>` | Injeção dinâmica do script responsável pela formatação dos links de checkout ou tracking de conversão na oferta. |

---

### 4.2. Implementação no Template `index`

Todo arquivo `index.html` deve obrigatoriamente possuir o **Tracking Script Nativo** (a versão segura que remove o `www.` e resolve a URL do script dinamicamente) e o placeholder `{{checkout_script}}` logo abaixo dele, antes do fechamento da tag `<head>`.

**Exemplo de estrutura no `index.html`:**
```html
<head>
    {{checkout_script}}
    ...
    {{vturb_preload}}

    <script type="text/javascript">
        (function () {
            // Remove 'www.' do início para garantir que sempre use o domínio raiz
            const currentDomain = window.location.hostname.replace(/^www\./, '');

            const trackScript = document.createElement('script');
            trackScript.type = 'text/javascript';
            trackScript.src = `https://lp.${currentDomain}/track.js`;
            document.head.appendChild(trackScript);
        })();
    </script>

</head>
```

---

### 4.3. Implementação no Template `offer`

A página de ofertas tem um comportamento diferente. Ela é responsável por carregar a inteligência de clique e mapeamento dos botões no momento da conversão. Para isso, utiliza-se exclusivamente o placeholder `{{track_checkout}}` posicionado antes do fechamento do documento.

**Exemplo de estrutura no `offer.html`:**
```html
    {{track_checkout}}
</body>
</html>
```

---

## 5. Exemplos Práticos de Implementação

### 5.1. Exemplo do Arquivo `index.html` (Focado no Vturb, Copy e Iframe de Oferta)

Este arquivo é a "casca" principal da sua VSL. Ele contém toda a infraestrutura de rastreamento no `<head>` e utiliza um modelo de carregamento embutido (iframe) para a seção de checkout, gerenciando a exibição através do script de delay do Vturb.

Para manter o arquivo limpo e focar no que importa para a automação, abaixo está o esqueleto da estrutura exigida:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {{checkout_script}}
    ...
    
    <script type="text/javascript">
        (function () {
            const currentDomain = window.location.hostname.replace(/^www\./, '');
            const trackScript = document.createElement('script');
            trackScript.type = 'text/javascript';
            trackScript.src = `https://lp.${currentDomain}/track.js`;
            document.head.appendChild(trackScript);
        })();
    </script>

    {{vturb_preload}}
    
    ...

</head>
<body>
    
    <h1 ...>{{headline}}</h1>
    ...
    <div class="video-embed">
        {{vturb_script}}
    </div>
    ...
    <iframe class="invisible" id="potes-frame" src="{{nome_arquivo_offer}}" style="border:none; width:100%;" scrolling="no" loading="lazy"></iframe>
    ...
    <script>
        // A automação injeta o tempo total em segundos aqui
        var delaySeconds = {{pit_delay}}; 
        var player = document.querySelector("vturb-smartplayer");

        player.addEventListener("player:ready", function () {
            // Revela todos os elementos com a classe '.invisible' (como o iframe de oferta) após o tempo estipulado
            player.displayHiddenElements(delaySeconds, [".invisible"], {
                persist: true,
            });
        });
    </script>

</body>
</html>
```
#### Pontos de Atenção para o Desenvolvedor Front-end neste Layout:
* [cite_start]**Ordem do `<head>`:** O `{{checkout_script}}` deve vir primeiro para garantir que a resolução do domínio ocorra o mais rápido possível, seguido pelos placeholders `{{vturb_preload}}` e Script Nativo[cite: 1].
* [cite_start]**A Classe `.invisible`:** Todos os elementos que só devem aparecer após o pitch de vendas (principalmente o iframe da oferta) devem obrigatoriamente carregar a classe `.invisible`[cite: 1]. [cite_start]O script no final do corpo da página usará essa classe junto com o `{{pit_delay}}` para revelar o conteúdo[cite: 1].
* **Iframe de Oferta Fixo:** O atributo `src` do iframe **não pode** ser `offer.html` de forma estática, nem um nome dinâmico informado pelo operador. Ele deve sempre utilizar o placeholder `{{nome_arquivo_offer}}`, que o compilador resolve para `"offer/"` — apontando para a sub-pasta `offer/index.html` servida pelo GitHub Pages.

### 5.2. Exemplo do Arquivo `offer.html` (Focado nos Cards, CSS e Script de Checkout)

O layout da página de ofertas pode variar drasticamente (podendo ser uma vitrine direta ou o final de um funil interativo/quiz). No entanto, o "motor" de conversão deve seguir rigorosamente a injeção de CSS no `<head>` e a estrutura de botões agnósticos, finalizando com o script dinâmico no final do `<body>`.

Abaixo está o esqueleto arquitetural de como um template de oferta (mesmo com designs complexos) deve ser construído:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Ofertas Especiais - {{nome_produto}}</title>
    
    <style>
        /* 1. CSS Exclusivo para injeção dinâmica de paleta (Obrigatório) */
        :root {
            --cor-card-fundo: {{cor_primaria}};
            --cor-card-botao: {{cor_secundaria}};
            --cor-card-fonte: {{cor_background}};
        }
        
        /* A partir daqui, o desenvolvedor está livre para adicionar todo o CSS 
           estrutural da página (grids, animações, quizzes, responsividade, etc.) */
        .ofertas-container { display: flex; gap: 18px; justify-content: center; }
        .btn { background: var(--cor-card-botao); color: #fff; }
        /* ... */
    </style>
</head>
<body>

    ...

    {{track_checkout}}

</body>
</html>
```

#### Pontos de Atenção para o Desenvolvedor Front-end (Offer):
* **Variedade de Layouts:** Não importa se a página é apenas um catálogo de potes (`neuro.html`) ou se possui um funil dinâmico e telas de carregamento (`quiz.html`), as variáveis declaradas no `:root` são a única forma do sistema pintar os cards com as cores do produto ativo.
* **Proibição de `data-click-path` manual:** Embora o script renderizado no final utilize o `data-click-path`, o desenvolvedor do template **NÃO** deve escrevê-lo manualmente no HTML. Use sempre os placeholders `{{attr_botao_X_potes}}`. A automação injetará o formato correto, garantindo que se o padrão de tracking mudar no futuro, os templates não precisem ser reescritos.
* **O Placeholder `{{track_checkout}}`:** Diferente do `index` (que tem rastreio nativo de visitas), a `offer` precisa deste placeholder no final do código. Ele será o responsável por cuspir o script que resolve a base da URL dinâmica e injeta a ação de clique nos botões gerados.