"""Predicados de intenção usados pela seleção híbrida de tools.

Cada predicado reutiliza os detectores determinísticos por domínio
(`agents/nlu/detectors.py` e `agents/nlu/extractors.py`) e expõe apenas o sinal
que a seleção precisa: qual tool candidata uma pergunta sugere.

São o ponto de aterrissagem das poucas distinções genuinamente ambíguas que o
chatbot cidadão preserva de forma determinística (emenda vs. transferência,
lista vs. agregado por função, ranking de contratos por valor vs. por contagem,
métricas de estoque). As demais decisões ficam a cargo do seletor LLM.
"""

from __future__ import annotations

from agents.nlu.constants import (
    DESPESAS_DOMAIN_KEYWORDS,
    DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS,
    DIARIAS_DOMAIN_KEYWORDS,
    PASSAGENS_DOMAIN_KEYWORDS,
)
from agents.nlu.detectors import (
    _extract_despesas_por_funcao_group_by,
    _extract_despesas_por_funcao_metric,
    _has_estoques_aggregate_intent,
    _is_despesas_por_funcao_query,
    _is_emenda_query,
    _is_estoques_movement_history_query,
    _is_estoques_query,
    _is_transferencias_financeiras_query,
    strip_despesas_por_funcao_domain_keywords,
)
from agents.nlu.extractors import (
    _is_contratos_dimension_count_ranking_query,
    _is_contratos_query,
)


_CONTRATOS_VALUE_RANKING_CUES = ("maiores", "maior", "top")
_TRANSFERENCIAS_AGGREGATION_CUES = (
    "quanto",
    "total",
    "totais",
    "quantos",
    "quantas",
    "por ",
    "quem recebeu",
    "quem repassou",
)


def contract_count_ranking_query(normalized_text: str) -> bool:
    """Ranking agregado de contratos por dimensão (fornecedor/secretaria/categoria)."""

    return _is_contratos_dimension_count_ranking_query(normalized_text)


def contract_value_ranking_query(normalized_text: str) -> bool:
    """Ranking de contratos individuais por valor ("maiores contratos")."""

    return _is_contratos_query(normalized_text) and any(
        cue in normalized_text for cue in _CONTRATOS_VALUE_RANKING_CUES
    )


def emenda_tool(normalized_text: str) -> str | None:
    """Tool de transferências para perguntas de emenda parlamentar (ou None)."""

    if not _is_transferencias_financeiras_query(normalized_text):
        return None
    if not _is_emenda_query(normalized_text):
        return None

    blocks_aggregation = "maiores" in normalized_text and any(
        cue in normalized_text for cue in ("quais", "liste", "mostre")
    )
    is_aggregation = not blocks_aggregation and any(cue in normalized_text for cue in _TRANSFERENCIAS_AGGREGATION_CUES)
    return "agregar_transferencias_financeiras" if is_aggregation else "consultar_transferencias_financeiras"


def estoque_tool(normalized_text: str) -> str | None:
    """Tool de estoque sugerida (saldo, agregado ou movimentações), ou None."""

    if not _is_estoques_query(normalized_text):
        return None
    if _is_estoques_movement_history_query(normalized_text):
        return "consultar_movimentacoes_de_estoque"
    if _has_estoques_aggregate_intent(normalized_text):
        return "agregar_estoques"
    return "consultar_estoques"


def is_function_spend_broad_total(normalized_text: str) -> bool:
    """ "Total gasto com [função]" amplo, sem agrupamento nem estágio específico.

    Mantém a regra dos quatro estágios: um total amplo de uma função de governo
    deve ir para `consultar_despesas_por_funcao` (que expõe empenhado, em
    liquidação, liquidado e pago), não colapsar num único `valor_pago` agregado.
    """

    if not _is_despesas_por_funcao_query(normalized_text):
        return False
    aggregation_text = strip_despesas_por_funcao_domain_keywords(normalized_text)
    if not any(cue in aggregation_text for cue in ("quanto", "total", "maior", "maiores", "por ", "quantas")):
        return False
    metrica = _extract_despesas_por_funcao_metric(normalized_text, aggregation_text)
    agrupar_por = _extract_despesas_por_funcao_group_by(aggregation_text)
    return metrica == "soma_valor_pago" and agrupar_por is None


def direct_spend_domain_tools(normalized_text: str) -> list[str] | None:
    """Classifica um gasto amplo no domínio estruturado correto (lista detalhada)."""

    if _has_any_term(normalized_text, DESPESAS_POR_FUNCAO_DOMAIN_KEYWORDS):
        return ["consultar_despesas_por_funcao"]
    if _has_any_term(normalized_text, DIARIAS_DOMAIN_KEYWORDS):
        return ["consultar_diarias"]
    if _has_any_term(normalized_text, PASSAGENS_DOMAIN_KEYWORDS):
        return ["consultar_passagens"]
    if _has_any_term(normalized_text, DESPESAS_DOMAIN_KEYWORDS):
        return ["consultar_despesas"]
    if _is_despesas_por_funcao_query(normalized_text):
        return ["consultar_despesas_por_funcao"]
    if "prefeitura gastou" in normalized_text or "valor gasto" in normalized_text:
        return ["consultar_despesas"]
    return None


def _has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
