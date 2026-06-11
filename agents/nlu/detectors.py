"""Detectores determinísticos de domínio reutilizados pela seleção híbrida.

Estas funções identificam o domínio/forma de uma pergunta (estoques,
transferências/emendas, despesas por função) e retornam apenas sinais simples
(booleanos/strings) consumidos pelos predicados de `intents`. Foram extraídas
das antigas regras de roteamento ao remover o router legado.
"""

from __future__ import annotations

import re

from agents.nlu.constants import (
    DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS,
    ESTOQUES_DOMAIN_KEYWORDS,
    TRANSFERENCIAS_FINANCEIRAS_DOMAIN_KEYWORDS,
)
from agents.nlu.extractors import (
    _contains_any,
    _contains_any_term,
    _contains_term,
)

# --- Transferências financeiras / emendas ------------------------------------


def _is_transferencias_financeiras_query(normalized_text: str) -> bool:
    return _contains_any_term(
        normalized_text,
        TRANSFERENCIAS_FINANCEIRAS_DOMAIN_KEYWORDS,
    )


def _is_emenda_query(normalized_text: str) -> bool:
    return _contains_any_term(
        normalized_text,
        (
            "emenda",
            "emendas",
            "ementa",
            "ementas",
            "parlamentar",
            "parlamentares",
        ),
    )


# --- Estoques ----------------------------------------------------------------

_ESTOQUES_MOVEMENT_KEYWORDS = (
    "movimentacao",
    "movimentacoes",
    "requisicao",
    "requisicoes",
    "aplicacao imediata",
    "nota fiscal de compra",
    "almoxarifado",
)
_ESTOQUES_AGGREGATION_KEYWORDS = (
    "quanto",
    "total",
    "totais",
    "comum",
    "comuns",
    "frequente",
    "frequentes",
    "maior",
    "maiores",
    "mais",
    "ranking",
    "quantas",
    "quantos",
)
_ESTOQUES_ENTITY_TERMS = (
    "material",
    "materiais",
    "item",
    "itens",
    "produto",
    "produtos",
)
_ESTOQUES_GENERIC_SIGNAL_TERMS = (
    "saldo",
    "entrada",
    "entradas",
    "saida",
    "saidas",
    "movimentacao",
    "movimentacoes",
    "almoxarifado",
)


def _is_estoques_query(normalized_text: str) -> bool:
    if _contains_any(normalized_text, ESTOQUES_DOMAIN_KEYWORDS):
        return True

    has_entity = any(_contains_term(normalized_text, term) for term in _ESTOQUES_ENTITY_TERMS)
    has_stock_signal = any(_contains_term(normalized_text, term) for term in _ESTOQUES_GENERIC_SIGNAL_TERMS)
    return has_entity and has_stock_signal


def _has_estoques_aggregate_intent(normalized_text: str) -> bool:
    return any(keyword in normalized_text for keyword in _ESTOQUES_AGGREGATION_KEYWORDS)


def _is_estoques_movement_history_query(normalized_text: str) -> bool:
    if any(
        keyword in normalized_text
        for keyword in (
            "requisicao",
            "requisicoes",
            "aplicacao imediata",
            "nota fiscal de compra",
        )
    ):
        return True
    if "historico" in normalized_text:
        return True
    if any(keyword in normalized_text for keyword in _ESTOQUES_MOVEMENT_KEYWORDS):
        return not _has_estoques_aggregate_intent(normalized_text)
    return False


# --- Despesas por função -----------------------------------------------------

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


# Ordem importa: pistas mais específicas ("dotacao inicial") antes das genéricas.
_DESPESAS_POR_FUNCAO_METRIC_CUES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("dotacao inicial",), "soma_dotacao_inicial"),
    (("creditos adicionais", "reducoes"), "soma_creditos_adicionais"),
    (("dotacao atualizada",), "soma_dotacao_atualizada"),
    (("em liquidacao",), "soma_valor_em_liquidacao"),
    (("liquidado",), "soma_valor_liquidado"),
    (("empenhado",), "soma_valor_empenhado"),
)


def _extract_despesas_por_funcao_metric(normalized_text: str, aggregation_text: str) -> str:
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
        and any(token in aggregation_text for token in ("quais", "maior", "maiores", "ranking"))
    ):
        return "funcao"
    return None
