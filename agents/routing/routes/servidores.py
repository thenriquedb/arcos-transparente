"""Regras de roteamento para consultas públicas de servidores."""

from __future__ import annotations

from agents.routing.extractors import _extract_limit, _extract_secretaria
from agents.routing.models import RouteDecision


def _try_route_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para agregações e rankings do domínio municipal.

    Casos que devem retornar RouteDecision:
        "qual secretaria com mais funcionarios"
        "quantas pessoas trabalham na saude"
        "quais os 10 maiores salarios da prefeitura"

    Casos que devem retornar None:
        "salario do pedro oliveira" -> vai para _try_route_historico
        "funcionarios da saude"     -> vai para _try_route_lista
        "como programar em python"  -> fallback do router
    """
    if "qual secretaria" in normalized_text and "mais funcionario" in normalized_text:
        return RouteDecision(
            domain="servidores",
            operation_type="agregacao_ranking",
            tool_name="agregar_servidores",
            tool_kwargs={
                "agrupar_por": "secretaria",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": 1,
            },
            tags=["scope:public", "domain:servidores", "shape:aggregate"],
            confident=True,
        )

    # Perguntas de "quantos" só viram agregação quando identificamos uma secretaria.
    if any(keyword in normalized_text for keyword in ("quantas", "quantos", "total de")):
        secretaria = _extract_secretaria(normalized_text)
        if secretaria:
            if secretaria == "saude":
                return RouteDecision(
                    domain="servidores",
                    operation_type="agregacao_ranking",
                    tool_name="agregar_servidores",
                    tool_kwargs={
                        "filtros": {"secretaria": secretaria},
                        "agrupar_por": "secretaria",
                        "metrica": "contagem",
                        "ordenar_por": "metrica",
                        "ordem": "desc",
                        "limite": 100,
                    },
                    tags=["scope:public", "domain:servidores", "shape:aggregate"],
                    confident=True,
                )
            return RouteDecision(
                domain="servidores",
                operation_type="agregacao_ranking",
                tool_name="agregar_servidores",
                tool_kwargs={
                    "filtros": {"secretaria": secretaria},
                    "metrica": "contagem",
                },
                tags=["scope:public", "domain:servidores", "shape:aggregate"],
                confident=True,
            )

    if "salario" in normalized_text and any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        return RouteDecision(
            domain="servidores",
            operation_type="consulta_lista",
            tool_name="consultar_servidores",
            tool_kwargs={
                "ordenar_por": "salario_base",
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
                "campos": [
                    "nome",
                    "salario_base",
                    "cargo",
                    "secretaria",
                    "mes_de_referencia",
                ],
            },
            tags=["scope:public", "domain:servidores", "shape:lookup"],
            confident=True,
        )
    return None


def _try_route_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens filtradas de servidores.

    Casos que devem retornar RouteDecision:
        "lista de todos os funcionarios da educacao"
        "quais servidores trabalham na saude"
        "liste os funcionarios da procuradoria"

    Casos que devem retornar None:
        "salario do pedro oliveira" -> vai para _try_route_historico
        "quantos trabalham na saude" -> vai para _try_route_agregacao
        "maiores salarios"          -> vai para _try_route_agregacao
    """
    secretaria = _extract_secretaria(normalized_text)
    if secretaria and any(
        keyword in normalized_text for keyword in ("lista", "liste", "funcionario", "trabalha", "trabalham")
    ):
        return RouteDecision(
            domain="servidores",
            operation_type="consulta_lista",
            tool_name="consultar_servidores",
            tool_kwargs={
                "filtros": {"secretaria": secretaria},
                "ordenar_por": "nome",
                "ordem": "asc",
            },
            tags=["scope:public", "domain:servidores", "shape:lookup"],
            confident=True,
        )
    return None
