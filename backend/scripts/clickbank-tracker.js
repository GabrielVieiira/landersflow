/**
 * ClickBank Tracker Script
 * Injetado via {{checkout_script}} no <head> do index.html para produtos ClickBank.
 *
 * Responsabilidades:
 * - Inicializa o script de afiliado do ClickBank
 * - Configura o vendor code para atribuição de vendas
 * - Lê parâmetros de afiliado da URL (tid, aff_sub1)
 *
 * NOTA: Este arquivo é lido pelo back-end via slug_aplicacao='clickbank'
 * e injetado no placeholder {{checkout_script}} durante a compilação.
 * Não edite os placeholders abaixo — eles são substituídos em runtime.
 */

(function () {
    // Inicializa rastreamento ClickBank
    var cbParams = {
        vendor: "{{VENDOR_CODE}}",  // Substituído pelos params EAV do produto
    };

    // Lê parâmetros de afiliado da URL para passar ao checkout
    var urlParams = new URLSearchParams(window.location.search);
    var tid = urlParams.get('tid') || '';
    var affSub = urlParams.get('aff_sub1') || urlParams.get('sub') || '';

    if (tid) cbParams.tid = tid;
    if (affSub) cbParams.aff_sub1 = affSub;

    // Injeta o script do ClickBank
    var cbScript = document.createElement('script');
    cbScript.type = 'text/javascript';
    cbScript.src = 'https://www.googletagmanager.com/gtag/js';
    document.head.appendChild(cbScript);
})();
