"""Regras de roteamento para o relatorio `despesas-por-funcao`."""

from __future__ import annotations

import re

from agents.routing.constants import DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS
from agents.routing.extractors import _contains_any, _extract_limit, _extract_year
from agents.routing.models import RouteDecision


_DESPESAS_POR_FUNCAO_SPEND_SIGNAL_KEYWORDS = (
    "gasto",
    "gastos",
    "gastou",
    "custo",
    "custos",
    "custou",
    "valor gasto",
    "pago",
    "pagos",
    "despesa",
    "despesas",
    "investido",
    "investida",
    "investimento",
)

_FUNCOES_DE_GOVERNO_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("assistencia social", ("assistencia social", "assistencia")),
    ("desporto e lazer", ("desporto", "esporte", "lazer")),
    ("direitos da cidadania", ("direitos da cidadania", "cidadania")),
    ("gestao ambiental", ("gestao ambiental", "meio ambiente", "ambiental")),
    ("previdencia social", ("previdencia social", "previdencia")),
    ("seguranca publica", ("seguranca publica", "seguranca")),
    (
        "urbanismo",
        (
            "urbanismo",
            "obra",
            "obras",
            "pavimentacao",
            "pavimentacoes",
            "calcamento",
            "infraestrutura urbana",
        ),
    ),
    ("administracao", ("administracao",)),
    ("agricultura", ("agricultura",)),
    ("cultura", ("cultura",)),
    ("educacao", ("educacao", "ensino")),
    ("energia", ("energia",)),
    ("habitacao", ("habitacao", "moradia", "moradias")),
    ("legislativa", ("legislativa", "legislativo")),
    ("saude", ("saude",)),
    ("saneamento", ("saneamento", "esgoto")),
    ("trabalho", ("trabalho", "emprego", "empregos")),
    ("transporte", ("transporte", "mobilidade", "transito")),
)


def _extract_funcao_de_governo_alias(normalized_text: str) -> str | None:
    for funcao, aliases in _FUNCOES_DE_GOVERNO_ALIASES:
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", normalized_text):
                return funcao
    return None


def _extract_funcao_de_governo(normalized_text: str) -> str | None:
    for funcao, aliases in _FUNCOES_DE_GOVERNO_ALIASES:
        for alias in aliases:
            if re.search(
                rf"\b(?:na|no|da|do|com|em|para)\b\s+{re.escape(alias)}\b",
                normalized_text,
            ):
                return funcao
    return None


def strip_despesas_por_funcao_domain_keywords(normalized_text: str) -> str:
    """Remove os termos do relatorio para inspecionar so o resto da pergunta."""

    stripped = normalized_text
    for keyword in DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS:
        stripped = stripped.replace(keyword, " ")
    return " ".join(stripped.split())


def _is_despesas_por_funcao_query(normalized_text: str) -> bool:
    if _contains_any(normalized_text, DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS):
        return True
    if _extract_funcao_de_governo(normalized_text) and any(
        token in normalized_text for token in _DESPESAS_POR_FUNCAO_SPEND_SIGNAL_KEYWORDS
    ):
        return True
    return (
        any(token in normalized_text for token in ("funcao", "funcoes"))
        and "despesa" in normalized_text
        and any(
            token in normalized_text
            for token in (
                "dotacao",
                "creditos adicionais",
                "valor empenhado",
                "valor liquidado",
                "valor pago",
            )
        )
    )


def _extract_despesas_por_funcao_filters(normalized_text: str) -> dict[str, object]:
    filtros: dict[str, object] = {}
    if year := _extract_year(normalized_text):
        filtros["ano"] = year
    if "fumusa" in normalized_text:
        filtros["origem"] = "saude"
    elif "prefeitura" in normalized_text:
        filtros["origem"] = "prefeitura"
    elif "camara" in normalized_text:
        filtros["origem"] = "camara"

    unidade_match = re.search(
        r"\bunidade gestora\b\s+(?:da|de|do)?\s*([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        normalized_text,
    )
    if unidade_match is not None:
        filtros["unidade_gestora"] = " ".join(unidade_match.group(1).split())

    funcao_match = re.search(
        r"\bfunc(?:ao|oes)\b\s+(?:da|de|do|na|no)?\s*([a-z0-9 .&/-]+?)(?=\s+\bem\b\s+\d{4}\b|\?|$)",
        normalized_text,
    )
    if funcao_match is not None:
        valor = " ".join(funcao_match.group(1).split())
        valor_sem_pontuacao = valor.strip(" .")
        if (
            valor
            and "despesas por funcao" not in valor
            and re.fullmatch(r"(?:em\s+)?\d{4}", valor_sem_pontuacao) is None
        ):
            filtros["funcao"] = _extract_funcao_de_governo_alias(valor) or valor
    elif funcao := _extract_funcao_de_governo(normalized_text):
        filtros["funcao"] = funcao

    return filtros


# Ordem importa: pistas mais específicas ("dotacao inicial") antes das genéricas.
_DESPESAS_POR_FUNCAO_METRIC_CUES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("dotacao inicial",), "soma_dotacao_inicial"),
    (("creditos adicionais", "reducoes"), "soma_creditos_adicionais"),
    (("dotacao atualizada",), "soma_dotacao_atualizada"),
    (("em liquidacao",), "soma_valor_em_liquidacao"),
    (("liquidado",), "soma_valor_liquidado"),
    (("empenhado",), "soma_valor_empenhado"),
)


def _extract_despesas_por_funcao_metric(
    normalized_text: str, aggregation_text: str
) -> str:
    """Escolhe a métrica do relatório citada na pergunta (default: valor pago)."""

    if "quantas" in aggregation_text:
        return "contagem"
    for cues, metrica in _DESPESAS_POR_FUNCAO_METRIC_CUES:
        if any(cue in normalized_text for cue in cues):
            return metrica
    return "soma_valor_pago"


def _extract_despesas_por_funcao_group_by(aggregation_text: str) -> str | None:
    """Escolhe a dimensão de agrupamento pedida na pergunta."""

    if "por origem" in aggregation_text:
        return "origem"
    if "por unidade" in aggregation_text or "por unidade gestora" in aggregation_text:
        return "unidade_gestora"
    if "por ano" in aggregation_text or "por exercicio" in aggregation_text:
        return "ano"
    if "por funcao" in aggregation_text or (
        "funcoes" in aggregation_text
        and any(
            token in aggregation_text
            for token in ("quais", "maior", "maiores", "ranking")
        )
    ):
        return "funcao"
    return None


def _try_route_despesas_por_funcao_agregacao(
    normalized_text: str,
) -> RouteDecision | None:
    if not _is_despesas_por_funcao_query(normalized_text):
        return None
    aggregation_text = strip_despesas_por_funcao_domain_keywords(normalized_text)
    if not any(
        keyword in aggregation_text
        for keyword in ("quanto", "total", "maior", "maiores", "por ", "quantas")
    ):
        return None

    filtros = _extract_despesas_por_funcao_filters(normalized_text)
    metrica = _extract_despesas_por_funcao_metric(normalized_text, aggregation_text)
    agrupar_por = _extract_despesas_por_funcao_group_by(aggregation_text)

    return RouteDecision(
        domain="despesas_por_funcao",
        operation_type="agregacao_ranking",
        tool_name="agregar_despesas_por_funcao",
        tool_kwargs={
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": "metrica",
            "ordem": "desc",
            "limite": _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:despesas_por_funcao", "shape:aggregate"],
        confident=True,
    )


def _try_route_despesas_por_funcao_lista(normalized_text: str) -> RouteDecision | None:
    if not _is_despesas_por_funcao_query(normalized_text):
        return None

    filtros = _extract_despesas_por_funcao_filters(normalized_text)
    return RouteDecision(
        domain="despesas_por_funcao",
        operation_type="consulta_lista",
        tool_name="consultar_despesas_por_funcao",
        tool_kwargs={
            "filtros": filtros,
            "ordenar_por": "valor_pago"
            if any(keyword in normalized_text for keyword in ("maior", "maiores"))
            else "periodo_fim",
            "ordem": "desc",
            "limite": 100
            if any(keyword in normalized_text for keyword in ("todos", "todas"))
            else _extract_limit(normalized_text, default=10),
        },
        tags=["scope:public", "domain:despesas_por_funcao", "shape:lookup"],
        confident=True,
    )
