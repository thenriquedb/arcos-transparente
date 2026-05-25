"""Router deterministico de intencao para reduzir o conjunto de tools expostas."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from agents.tools.registry import get_public_tools
from agents.tools.sql_tools.planejamento.shared.entities import (
    extract_planejamento_entidade_alias,
)


Domain = Literal[
    "servidores",
    "folha_pagamento",
    "licitacoes",
    "planejamento",
    "desconhecido",
]
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
    "licitacao",
    "licitacoes",
    "pregao",
    "pregoes",
    "edital",
    "editais",
    "fornecedor",
    "fornecedores",
    "vencedor",
    "vencedores",
    "contrato",
    "contratos",
    "instrumento",
    "instrumentos",
    "planejamento",
    "planejamentos",
    "orcamento",
    "orcamentario",
    "orcamentaria",
    "dotacao",
    "empenhado",
    "liquidado",
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
    "fumusa",
)

SUPPORTED_SCOPE_WEAK_KEYWORDS = (
    "salario",
    "salarios",
    "recebeu",
    "recebe",
    "gasto",
    "gastos",
    "pago",
    "pagos",
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


def _extract_planejamento_entidade(normalized_text: str) -> str | None:
    return extract_planejamento_entidade_alias(normalized_text)


def _is_licitacoes_query(normalized_text: str) -> bool:
    return any(
        keyword in normalized_text
        for keyword in (
            "licitacao",
            "licitacoes",
            "pregao",
            "pregoes",
            "edital",
            "editais",
            "contrato",
            "contratos",
            "instrumento",
            "instrumentos",
        )
    )


def _extract_licitacao_numero(normalized_text: str) -> str | None:
    match = re.search(
        r"\b(?:numero|n|licitacao|pregao)\b\s+([0-9][0-9./-]*)\b",
        normalized_text,
    )
    if match is None:
        return None
    return match.group(1).strip()


def _extract_year(normalized_text: str) -> int | None:
    match = re.search(r"\b(20\d{2})\b", normalized_text)
    if match is None:
        return None
    return int(match.group(1))


def _is_planejamento_query(normalized_text: str) -> bool:
    if any(
        keyword in normalized_text
        for keyword in (
            "planejamento",
            "planejamentos",
            "orcamento",
            "orcamentario",
            "orcamentaria",
            "dotacao",
            "empenhado",
            "liquidado",
        )
    ):
        return True

    if _extract_planejamento_entidade(normalized_text) and any(
        keyword in normalized_text
        for keyword in (
            "planejado",
            "planejada",
            "recurso",
            "recursos",
            "verba",
            "verbas",
            "programa",
            "acao",
            "acoes",
            "gasto",
            "gastos",
            "pago",
            "pagos",
        )
    ):
        return True

    return "saude" in normalized_text and any(
        keyword in normalized_text
        for keyword in ("gasto", "gastos", "pago", "pagos", "planejado")
    )


def _extract_planejamento_filters_from_query(normalized_text: str) -> dict[str, Any]:
    filtros: dict[str, Any] = {"origem": "saude"}
    entidade = _extract_planejamento_entidade(normalized_text)
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "primeiro trimestre" in normalized_text or "1 trimestre" in normalized_text:
        filtros["mes_inicio"] = 1
        filtros["mes_fim"] = 3
    elif "segundo trimestre" in normalized_text or "2 trimestre" in normalized_text:
        filtros["mes_inicio"] = 4
        filtros["mes_fim"] = 6
    elif "terceiro trimestre" in normalized_text or "3 trimestre" in normalized_text:
        filtros["mes_inicio"] = 7
        filtros["mes_fim"] = 9
    elif "quarto trimestre" in normalized_text or "4 trimestre" in normalized_text:
        filtros["mes_inicio"] = 10
        filtros["mes_fim"] = 12
    if entidade is not None:
        filtros["entidade"] = entidade
    if "saude" in normalized_text and entidade is None:
        filtros["area"] = "saude"
    return filtros


def _extract_planejamento_metric(normalized_text: str) -> str:
    if "inicial" in normalized_text:
        return "soma_orcamento_inicial"
    if "empenhado" in normalized_text or "comprometido" in normalized_text:
        return "soma_valor_comprometido"
    if "liquidado" in normalized_text or "confirmado" in normalized_text:
        return "soma_valor_confirmado"
    if any(keyword in normalized_text for keyword in ("pago", "pagos", "gasto")):
        return "soma_valor_pago"
    return "soma_orcamento_atualizado"


def _extract_licitacoes_objeto(normalized_text: str) -> str | None:
    if "festival gastronomico" in normalized_text:
        return "festival gastronomico"
    if "festival de gastronomia" in normalized_text:
        return "festival gastronomia"
    if "festival" in normalized_text:
        return "festival"
    return None


def _build_licitacoes_filters_from_query(normalized_text: str) -> dict[str, Any]:
    filtros: dict[str, Any] = {}
    if numero := _extract_licitacao_numero(normalized_text):
        filtros["numero"] = numero
        return filtros
    if secretaria := _extract_secretaria(normalized_text):
        filtros["secretaria"] = secretaria
    if objeto := _extract_licitacoes_objeto(normalized_text):
        filtros["objeto"] = objeto
    if year := _extract_year(normalized_text):
        filtros["data_abertura_inicio"] = f"{year}-01-01"
        filtros["data_abertura_fim"] = f"{year}-12-31"
    return filtros


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


def _try_route_licitacoes_agregacao(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para consultas agregadas e rankings de licitacoes.

    Casos que devem retornar RouteDecision:
        "quantas licitacoes existem na saude"
        "qual secretaria tem mais licitacoes"
        "quais as 10 maiores licitacoes"

    Casos que devem retornar None:
        "licitacao numero 12/2025" -> vai para _try_route_licitacoes_lista
        "salario do pedro"         -> vai para _try_route_historico
        "funcionarios da saude"    -> vai para _try_route_lista
    """
    if not _is_licitacoes_query(normalized_text):
        return None

    if any(
        keyword in normalized_text for keyword in ("todas", "todos", "quais")
    ) and any(
        keyword in normalized_text for keyword in ("total", "gasto", "gastos", "valor")
    ):
        return None

    if "qual secretaria" in normalized_text and "mais" in normalized_text:
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "agrupar_por": "secretaria",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
                "limite": 1,
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if "modalidade" in normalized_text and any(
        keyword in normalized_text for keyword in ("mais", "ranking", "quantidade")
    ):
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "agrupar_por": "modalidade",
                "metrica": "contagem",
                "ordenar_por": "metrica",
                "ordem": "desc",
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if any(
        keyword in normalized_text for keyword in ("quantas", "quantos", "total de")
    ):
        filtros = _build_licitacoes_filters_from_query(normalized_text)
        return RouteDecision(
            domain="licitacoes",
            operation_type="agregacao_ranking",
            tool_name="agregar_licitacoes",
            tool_kwargs={
                "filtros": filtros,
                "metrica": "contagem",
            },
            tags=["scope:public", "domain:licitacoes", "shape:aggregate"],
            confident=True,
        )

    if any(keyword in normalized_text for keyword in ("maiores", "maior", "top")):
        return RouteDecision(
            domain="licitacoes",
            operation_type="consulta_lista",
            tool_name="consultar_licitacoes",
            tool_kwargs={
                "ordenar_por": "valor_estimado",
                "ordem": "desc",
                "limite": _extract_limit(normalized_text, default=10),
                "campos": [
                    "numero",
                    "objeto",
                    "valor_estimado",
                    "secretaria",
                    "data_abertura",
                    "situacao",
                ],
            },
            tags=["scope:public", "domain:licitacoes", "shape:lookup"],
            confident=True,
        )

    return None


def _try_route_planejamento_agregacao(
    normalized_text: str,
) -> RouteDecision | None:
    """
    Roteia para totais e rankings do planejamento da saude.

    Casos que devem retornar RouteDecision:
        "quanto foi planejado para saude em 2025"
        "quanto foi pago em saude no primeiro trimestre de 2025"
        "quais acoes de saude tiveram maior orcamento"

    Casos que devem retornar None:
        "licitacoes da saude"       -> vai para _try_route_licitacoes_lista
        "funcionarios da saude"     -> vai para _try_route_lista
        "salario do pedro"          -> vai para _try_route_historico
    """
    if not _is_planejamento_query(normalized_text):
        return None

    if any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "mostre", "quais", "detalhe")
    ) and not any(
        keyword in normalized_text
        for keyword in ("maior", "maiores", "mais", "quanto", "total", "por mes")
    ):
        return None

    filtros = _extract_planejamento_filters_from_query(normalized_text)
    metrica = _extract_planejamento_metric(normalized_text)

    if any(keyword in normalized_text for keyword in ("por mes", "mes a mes")):
        agrupar_por = "mes"
    elif "programa" in normalized_text:
        agrupar_por = "programa"
    elif "subarea" in normalized_text or "subfuncao" in normalized_text:
        agrupar_por = "subarea"
    elif "acao" in normalized_text or "acoes" in normalized_text:
        agrupar_por = "acao"
    elif "grupo" in normalized_text or "tipo de gasto" in normalized_text:
        agrupar_por = "grupo_de_gasto"
    else:
        agrupar_por = None

    return RouteDecision(
        domain="planejamento",
        operation_type="agregacao_ranking",
        tool_name="agregar_planejamento",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:planejamento", "shape:aggregate"],
        confident=True,
    )


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


def _try_route_planejamento_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens do planejamento da saude.

    Casos que devem retornar RouteDecision:
        "liste o planejamento da saude em 2025"
        "mostre as acoes planejadas da saude"
        "quais linhas do orcamento da saude"

    Casos que devem retornar None:
        "quanto foi pago na saude"  -> vai para _try_route_planejamento_agregacao
        "licitacao numero 12/2025"  -> vai para _try_route_licitacoes_lista
        "funcionarios da saude"     -> vai para _try_route_lista
    """
    if not _is_planejamento_query(normalized_text):
        return None
    if not any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "mostre", "quais", "detalhe")
    ):
        return None

    filtros = _extract_planejamento_filters_from_query(normalized_text)
    return RouteDecision(
        domain="planejamento",
        operation_type="consulta_lista",
        tool_name="consultar_planejamento",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "mes_num",
            "ordem": "asc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todas", "todos"))
            else 10,
        },
        tags=["scope:public", "domain:planejamento", "shape:lookup"],
        confident=True,
    )


def _try_route_licitacoes_lista(normalized_text: str) -> RouteDecision | None:
    """
    Roteia para listagens e detalhes de licitacoes.

    Casos que devem retornar RouteDecision:
        "liste as licitacoes da saude"
        "detalhe a licitacao numero 12/2025"
        "quais licitacoes foram abertas"

    Casos que devem retornar None:
        "quantas licitacoes existem" -> vai para _try_route_licitacoes_agregacao
        "maiores licitacoes"         -> vai para _try_route_licitacoes_agregacao
        "funcionarios da saude"      -> vai para _try_route_lista
    """
    if not _is_licitacoes_query(normalized_text):
        return None

    filtros = _build_licitacoes_filters_from_query(normalized_text)
    incluir_detalhes = False

    if "numero" in filtros:
        incluir_detalhes = True
    if any(
        keyword in normalized_text
        for keyword in (
            "vencedor",
            "vencedores",
            "contrato",
            "contratos",
            "instrumento",
        )
    ):
        incluir_detalhes = True

    if filtros or any(
        keyword in normalized_text
        for keyword in ("lista", "liste", "quais", "detalhe", "mostre")
    ):
        limite = (
            100
            if any(keyword in normalized_text for keyword in ("todas", "todos"))
            else 10
        )
        return RouteDecision(
            domain="licitacoes",
            operation_type="consulta_lista",
            tool_name="consultar_licitacoes",
            tool_kwargs={
                "filtros": filtros,
                "ordenar_por": "data_abertura",
                "ordem": "desc",
                "limite": limite,
                "incluir_detalhes": incluir_detalhes,
            },
            tags=["scope:public", "domain:licitacoes", "shape:lookup"],
            confident=True,
        )

    return None


def route_user_query(query: str) -> RouteDecision:
    normalized_text = _normalize(query)

    # Prioridade 1 — histórico individual de servidor
    if route := _try_route_historico(normalized_text):
        return route

    # Prioridade 2 — rankings e agregações de licitações
    if route := _try_route_licitacoes_agregacao(normalized_text):
        return route

    # Prioridade 3 — rankings e agregações de planejamento
    if route := _try_route_planejamento_agregacao(normalized_text):
        return route

    # Prioridade 4 — rankings e agregações de servidores
    if route := _try_route_agregacao(normalized_text):
        return route

    # Prioridade 5 — listagens e detalhes de licitações
    if route := _try_route_licitacoes_lista(normalized_text):
        return route

    # Prioridade 6 — listagens de planejamento
    if route := _try_route_planejamento_lista(normalized_text):
        return route

    # Prioridade 7 — listagens com filtro de secretaria
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
                "licitações ou planejamento."
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
            "secretarias, salários-base, histórico de pagamentos, licitações "
            "e planejamento."
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
