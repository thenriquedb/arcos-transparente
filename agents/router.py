"""Router deterministico de intencao para reduzir o conjunto de tools expostas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from agents.tools.registry import get_public_tools


Domain = Literal["servidores", "folha_pagamento", "licitacoes", "desconhecido"]
OperationType = Literal[
    "consulta_lista",
    "agregacao_ranking",
    "historico_detalhado",
    "desconhecido",
]


@dataclass(slots=True)
class RouteDecision:
    domain: Domain
    operation_type: OperationType
    tool_name: str | None = None
    tool_kwargs: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=lambda: ["scope:public"])
    confident: bool = False


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.lower().strip()


def _extract_limit(normalized_text: str, default: int = 10) -> int:
    match = re.search(r"\b(\d{1,3})\b", normalized_text)
    if match is None:
        return default
    return int(match.group(1))


def _extract_secretaria(normalized_text: str) -> str | None:
    patterns = [
        r"(?:na|no|da|do)\s+(?:secretaria\s+de\s+)?([a-z0-9\s]+?)(?:\?|$)",
        r"funcionarios\s+da\s+([a-z0-9\s]+?)(?:\?|$)",
        r"trabalham\s+na\s+([a-z0-9\s]+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        secretaria = match.group(1).strip()
        if secretaria:
            return secretaria
    return None


def _extract_nome_para_historico(normalized_text: str) -> str | None:
    patterns = [
        r"salario\s+do\s+([a-z\s]+?)(?:\?|$)",
        r"quanto\s+([a-z\s]+?)\s+recebeu(?:\?|$)",
        r"pagamentos\s+do\s+([a-z\s]+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        nome = match.group(1).strip()
        if nome:
            return nome
    return None


def route_user_query(query: str) -> RouteDecision:
    normalized_text = _normalize(query)

    nome_para_historico = _extract_nome_para_historico(normalized_text)
    if nome_para_historico and all(keyword not in normalized_text for keyword in ("maiores", "ranking", "top")):
        return RouteDecision(
            domain="folha_pagamento",
            operation_type="historico_detalhado",
            tool_name="buscar_historico_de_pagamentos_do_servidor",
            tool_kwargs={"nome": nome_para_historico},
            tags=["scope:public", "domain:folha", "shape:history"],
            confident=True,
        )

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

    if any(keyword in normalized_text for keyword in ("quantas", "quantos", "total de")):
        secretaria = _extract_secretaria(normalized_text)
        if secretaria:
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

    if ("salario" in normalized_text and any(keyword in normalized_text for keyword in ("maiores", "maior", "top"))):
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

    secretaria = _extract_secretaria(normalized_text)
    if secretaria and any(keyword in normalized_text for keyword in ("lista", "liste", "funcionario", "trabalha", "trabalham")):
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

    return RouteDecision(
        domain="desconhecido",
        operation_type="desconhecido",
        tags=["scope:public"],
        confident=False,
    )


def select_public_tools_for_query(query: str | None = None) -> list[object]:
    if not query:
        return get_public_tools()

    route = route_user_query(query)
    if not route.confident:
        return get_public_tools()

    tools = get_public_tools(tags=route.tags[1:])
    return tools or get_public_tools()
