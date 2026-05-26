"""Regras de roteamento para histórico individual de folha."""

from __future__ import annotations

from agents.routing.extractors import _extract_nome_para_historico
from agents.routing.models import RouteDecision


def _try_route_historico(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para histórico detalhado de pagamentos de um servidor específico.

    Casos que devem retornar RouteDecision:
        "quanto joao silva recebeu"
        "salario do pedro oliveira"
        "pagamentos do servidor maria souza"

    Casos que devem retornar None:
        "maiores salarios"          -> vai para _try_route_agregacao
        "funcionarios da saude"     -> vai para _try_route_lista
        "quantos servidores tem"    -> vai para _try_route_agregacao
    """
    nome_para_historico = _extract_nome_para_historico(normalized_text)
    if nome_para_historico and all(
        keyword not in normalized_text for keyword in ("maiores", "ranking", "top")
    ):
        return RouteDecision(
            domain="folha_pagamento",
            operation_type="historico_detalhado",
            tool_name="buscar_historico_de_pagamentos_do_servidor",
            tool_kwargs={"nome": nome_para_historico},
            tags=["scope:public", "domain:folha", "shape:history"],
            confident=True,
        )
    return None
