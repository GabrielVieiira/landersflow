/**
 * Generic/Native Tracker Script
 * Injetado via {{track_checkout}} no final do <body> do offer.html
 * para plataformas genéricas (não-ClickBank).
 *
 * Responsabilidades:
 * - Resolve o domínio raiz (sem www.) dinamicamente
 * - Injeta o atributo de ação nos botões de checkout via data-click-path
 * - Compatível com o padrão RedTrack de roteamento de clicks
 *
 * NOTA: Este arquivo é lido pelo back-end via slug_aplicacao='generic-track'
 * e injetado no placeholder {{track_checkout}} durante a compilação.
 */

(function () {
    'use strict';

    // Resolve domínio raiz (remove www.)
    var currentDomain = window.location.hostname.replace(/^www\./, '');

    /**
     * Inicializa os botões de checkout com o handler de click do RedTrack.
     * Os atributos data-click-path já foram injetados pelo compilador
     * via {{attr_botao_X_potes}}.
     */
    function initCheckoutButtons() {
        var buttons = document.querySelectorAll('[data-click-path]');

        buttons.forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                var clickPath = btn.getAttribute('data-click-path');

                // Constrói a URL de click do RedTrack
                var clickUrl = 'https://lp.' + currentDomain + clickPath;

                // Preserva parâmetros UTM/tid da URL atual
                var urlParams = new URLSearchParams(window.location.search);
                var tid = urlParams.get('tid');
                if (tid) clickUrl += '?tid=' + encodeURIComponent(tid);

                window.location.href = clickUrl;
            });
        });
    }

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCheckoutButtons);
    } else {
        initCheckoutButtons();
    }
})();
