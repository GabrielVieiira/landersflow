"""
Exportações centralizadas dos modelos SQLModel.
Importar este módulo garante que todos os modelos estejam registrados
no metadata do SQLModel antes da criação das tabelas.
"""

# Importar na ordem correta (bases primeiro, derivados depois)
# Assim o SQLAlchemy registra as FKs na sequência certa
from backend.models.plataforma import Nicho, PlataformaCheckout       # sem FKs externas
from backend.models.dominio import Dominio, StatusDNS                  # FK: nicho
from backend.models.template import TipoTemplate, Template  # TipoTemplate primeiro (FK dep)
from backend.models.traffic import TrafficChannel, TrafficChannelPostback    # FK: traffic_channel
from backend.models.produto import Produto, ProdutoCheckoutParam, ProdutoVariacao  # FK: nicho, plataforma
from backend.models.lander import Lander                               # FK: produto, template, dominio
from backend.models.campanha import Campanha                           # FK: lander, traffic_channel

__all__ = [
    "Nicho",
    "PlataformaCheckout",
    "Produto",
    "ProdutoVariacao",
    "ProdutoCheckoutParam",
    "TipoTemplate",
    "Template",
    "Dominio",
    "StatusDNS",
    "Lander",
    "TrafficChannel",
    "TrafficChannelPostback",
    "Campanha",
]
