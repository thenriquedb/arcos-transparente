"""Registry of modulo de ingestao adapters used by IngestionPipeline."""

from __future__ import annotations

from .adapters import IngestionTypeAdapter
from .contratos import ADAPTER as CONTRATOS_ADAPTER
from .despesas import ADAPTER as DESPESAS_ADAPTER
from .eleitos import ADAPTER as ELEITOS_ADAPTER
from .estoques import ADAPTER as ESTOQUES_ADAPTER
from .folha_pagamento import ADAPTER as FOLHA_PAGAMENTO_ADAPTER
from .frotas import ADAPTER as FROTAS_ADAPTER
from .licitacoes import ADAPTER as LICITACOES_ADAPTER
from .patrimonios import ADAPTER as PATRIMONIOS_ADAPTER
from .planejamentos import ADAPTER as PLANEJAMENTOS_ADAPTER
from .quadro_pessoal import ADAPTER as QUADRO_PESSOAL_ADAPTER
from .receitas import ADAPTER as RECEITAS_ADAPTER
from .servidores import ADAPTER as SERVIDORES_ADAPTER
from .transferencias_financeiras import (
    ADAPTER as TRANSFERENCIAS_FINANCEIRAS_ADAPTER,
)


def build_adapter_registry() -> dict[str, IngestionTypeAdapter]:
    """Return adapters in the stable tipo ordering expected by the CLI/runtime."""

    return {
        "contratos": CONTRATOS_ADAPTER,
        "licitacoes": LICITACOES_ADAPTER,
        "frotas": FROTAS_ADAPTER,
        "estoques": ESTOQUES_ADAPTER,
        "servidores": SERVIDORES_ADAPTER,
        "receitas": RECEITAS_ADAPTER,
        "folha_pagamento": FOLHA_PAGAMENTO_ADAPTER,
        "planejamentos": PLANEJAMENTOS_ADAPTER,
        "despesas": DESPESAS_ADAPTER,
        "patrimonios": PATRIMONIOS_ADAPTER,
        "quadro_pessoal": QUADRO_PESSOAL_ADAPTER,
        "eleitos": ELEITOS_ADAPTER,
        "transferencias_financeiras": TRANSFERENCIAS_FINANCEIRAS_ADAPTER,
    }
