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
GuardrailCategory = Literal[
    "allowed",
    "out_of_scope",
    "prompt_injection",
    "empty_query",
]


@dataclass(slots=True)
class RouteDecision:
    domain: Domain
    operation_type: OperationType
    tool_name: str | None = None
    tool_kwargs: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=lambda: ["scope:public"])
    confident: bool = False


@dataclass(slots=True)
class GuardrailDecision:
    allowed: bool
    category: GuardrailCategory
    message: str | None = None


PROMPT_INJECTION_PATTERNS = (
    r"\b(?:ignore|disregard|override|bypass)\b.{0,80}\b(?:instruction|instructions|prompt|system|developer|rules?)\b",
    r"\b(?:desconsidere|ignore|ignore todas|ignore todos|ignore as|ignore os|burle|contorne)\b.{0,80}\b(?:instrucoes|instrução|instrucao|regras?|prompt|sistema|desenvolvedor|developer)\b",
    r"\b(?:revele|mostre|exiba|imprima|print|display)\b.{0,80}\b(?:prompt|system prompt|mensagem de sistema|developer message|mensagem do desenvolvedor)\b",
    r"\b(?:nao use|nao utilize|do not use|never use)\b.{0,30}\b(?:todas as tools|todas as ferramentas|any tools|nenhuma tool)\b",
)

SECRETARIAS_CONHECIDAS = (
    "saude",
    "educacao",
    "obras",
    "financas",
    "administracao",
    "procuradoria",
    "assistencia social",
    "meio ambiente",
    "planejamento",
    "transporte",
)

SUPPORTED_SCOPE_STRONG_KEYWORDS = (
    "prefeitura",
    "municipal",
    "servidor",
    "servidores",
    "funcionario",
    "funcionarios",
    "secretaria",
    "secretarias",
    "cargo",
    "cargos",
    "folha",
    "pagamento",
    "pagamentos",
)

SUPPORTED_SCOPE_WEAK_KEYWORDS = (
    "salario",
    "salarios",
    "recebeu",
    "recebe",
    "trabalha",
    "trabalham",
    "saude",
    "educacao",
    "obras",
    "procuradoria",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return without_accents.lower().strip()


def _extract_limit(normalized_text: str, default: int = 10) -> int:
    match = re.search(
        r"\b(?:top|maiores|menores|primeiro|primeiros|listar?|mostrar?|exibir?)\s+(\d{1,3})\b",
        normalized_text,
    )
    if match is None:
        return default
    return int(match.group(1))


def _extract_secretaria(normalized_text: str) -> str | None:
    patterns = [
        r"\b(?:na|no|da|do)\b\s+(?:secretaria\s+de\s+)?((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\bfuncionarios\b\s+\bda\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\btrabalham\b\s+\bna\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        candidato = " ".join(match.group(1).split())
        for secretaria in SECRETARIAS_CONHECIDAS:
            if secretaria in candidato:
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


def _contains_prompt_injection(normalized_text: str) -> bool:
    return any(
        re.search(pattern, normalized_text) is not None
        for pattern in PROMPT_INJECTION_PATTERNS
    )


def _count_keyword_hits(normalized_text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword in normalized_text)


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

    if any(
        keyword in normalized_text for keyword in ("quantas", "quantos", "total de")
    ):
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

    if "salario" in normalized_text and any(
        keyword in normalized_text for keyword in ("maiores", "maior", "top")
    ):
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
        keyword in normalized_text
        for keyword in ("lista", "liste", "funcionario", "trabalha", "trabalham")
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


def route_user_query(query: str) -> RouteDecision:
    normalized_text = _normalize(query)

    # Prioridade 1 — histórico individual de servidor
    if route := _try_route_historico(normalized_text):
        return route

    # Prioridade 2 — rankings e agregações
    if route := _try_route_agregacao(normalized_text):
        return route

    # Prioridade 3 — listagens com filtro de secretaria
    if route := _try_route_lista(normalized_text):
        return route

    # Fallback — deixa o LLM decidir com todas as tools
    return RouteDecision(
        domain="desconhecido",
        operation_type="desconhecido",
        tags=["scope:public"],
        confident=False,
    )


def evaluate_query_guardrails(
    query: str,
    route: RouteDecision | None = None,
) -> GuardrailDecision:
    normalized_text = _normalize(query)

    if not normalized_text:
        return GuardrailDecision(
            allowed=False,
            category="empty_query",
            message=(
                "Envie uma pergunta sobre os dados públicos municipais disponíveis "
                "no sistema, como servidores, secretarias, salários-base ou "
                "histórico de pagamentos."
            ),
        )

    if _contains_prompt_injection(normalized_text):
        return GuardrailDecision(
            allowed=False,
            category="prompt_injection",
            message=(
                "Não posso seguir pedidos para ignorar instruções, revelar prompts "
                "internos ou contornar regras do sistema. Posso ajudar apenas com "
                "consultas aos dados públicos municipais disponíveis."
            ),
        )

    route = route or route_user_query(query)
    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)

    if route.confident or strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(
            allowed=True,
            category="allowed",
        )

    return GuardrailDecision(
        allowed=False,
        category="out_of_scope",
        message=(
            "Posso ajudar apenas com consultas aos dados públicos municipais "
            "disponíveis neste sistema, especialmente sobre servidores, "
            "secretarias, salários-base e histórico de pagamentos."
        ),
    )


def select_public_tools_for_query(query: str | None = None) -> list[object]:
    if not query:
        return get_public_tools()

    route = route_user_query(query)
    guardrail = evaluate_query_guardrails(query, route=route)
    if not guardrail.allowed:
        return []

    if not route.confident:
        return get_public_tools()

    tools = get_public_tools(tags=route.tags[1:])
    return tools or get_public_tools()
