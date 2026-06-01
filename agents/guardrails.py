"""Guardrails compartilhados para perguntas cidadãs antes da execução do modelo."""

from __future__ import annotations

from collections.abc import Sequence
import re

from agents.routing.constants import (
    SUPPORTED_SCOPE_STRONG_KEYWORDS,
    SUPPORTED_SCOPE_WEAK_KEYWORDS,
)
from agents.routing.extractors import (
    _contains_prompt_injection,
    _count_keyword_hits,
    _extract_contrato_fornecedor,
    _extract_contratos_descricao,
    _extract_licitacoes_objeto,
    _extract_nome_para_historico,
    _extract_planejamento_area,
    _extract_planejamento_entidade,
    _extract_receitas_tema,
    _extract_receitas_unidade,
    _extract_secretaria,
    _extract_year,
    _normalize,
)
from agents.routing.models import GuardrailDecision, RouteDecision

_CONTEXTUAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:"
    r"dele|dela|deles|delas|"
    r"ele|ela|eles|elas|"
    r"esse|essa|esses|essas|"
    r"desse|dessa|desses|dessas|"
    r"disso|nisso|"
    r"nesse|nessa|nesses|nessas|"
    r"neste|nesta|nestes|nestas"
    r")\b"
)
_ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN = re.compile(
    r"^(?:e\s+)?(?:(?:o|a|os|as)\s+)?(?:(?:de|do|da|em)\s+)?20\d{2}\??$"
)
_PUBLIC_SPEND_SIGNAL_TERMS = (
    "custo",
    "custos",
    "custou",
    "gasto",
    "gastos",
    "pago",
    "pagos",
)
_SHORT_FOLLOW_UP_CONNECTOR_TOKENS = frozenset(
    {
        "e",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "do",
        "da",
        "dos",
        "das",
        "de",
        "com",
        "para",
        "por",
        "o",
        "a",
        "os",
        "as",
        "qual",
        "quais",
    }
)
_SHORT_RANKING_TOKENS = frozenset(
    {
        "maior",
        "maiores",
        "menor",
        "menores",
        "primeiro",
        "primeira",
        "primeiros",
        "primeiras",
        "ultimo",
        "ultima",
        "ultimos",
        "ultimas",
        "total",
        "totais",
        "valor",
        "valores",
    }
)
_SHORT_RANKING_STOPWORDS = frozenset(
    {
        "e",
        "qual",
        "quais",
        "o",
        "a",
        "os",
        "as",
        "de",
        "do",
        "da",
        "entre",
        "eles",
        "elas",
        "deles",
        "delas",
    }
)


def evaluate_public_query_guardrails(
    query: str,
    *,
    compatibility_route: RouteDecision | None = None,
    has_history: bool = False,
    prior_user_queries: Sequence[str] = (),
) -> GuardrailDecision:
    """Aplica bloqueios hard-coded antes da execução do modelo."""

    normalized_text = _normalize(query)

    if not normalized_text:
        return GuardrailDecision(
            allowed=False,
            category="empty_query",
            message=(
                "Envie uma pergunta sobre os dados públicos municipais disponíveis "
                "no sistema, como servidores, secretarias, salários-base ou "
                "licitações, despesas, patrimônio, planejamento, receitas "
                "ou políticos eleitos."
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

    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)

    has_public_context_anchor = _has_public_context_anchor(prior_user_queries)
    contextual_follow_up = _looks_like_contextual_follow_up(normalized_text)
    explicit_context_reference = _has_explicit_context_reference(normalized_text)

    if (
        has_history
        and explicit_context_reference
        and _has_inline_public_context_signal(
            normalized_text,
            strong_hits=strong_hits,
            weak_hits=weak_hits,
        )
    ):
        return GuardrailDecision(allowed=True, category="allowed")

    if has_history and contextual_follow_up and has_public_context_anchor:
        return GuardrailDecision(allowed=True, category="allowed")

    if compatibility_route is not None and compatibility_route.confident:
        return GuardrailDecision(allowed=True, category="allowed")

    if strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(allowed=True, category="allowed")

    if _looks_like_public_spend_query(normalized_text):
        return GuardrailDecision(allowed=True, category="allowed")

    return GuardrailDecision(
        allowed=False,
        category="out_of_scope",
        message=(
            "Posso ajudar apenas com consultas aos dados públicos municipais "
            "disponíveis neste sistema, especialmente sobre servidores, "
            "secretarias, salários-base, histórico de pagamentos, licitações, "
            "despesas, patrimônio, quadro de pessoal, planejamento, receitas "
            "e políticos eleitos."
        ),
    )


def _looks_like_contextual_follow_up(normalized_text: str) -> bool:
    """Permite continuação curta dependente de histórico sem forçar nova rota."""

    if _has_explicit_context_reference(normalized_text):
        return True
    if _ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN.fullmatch(normalized_text) is not None:
        return True
    if _looks_like_short_public_filter_follow_up(normalized_text):
        return True
    if _looks_like_short_ranking_follow_up(normalized_text):
        return True
    return False


def _looks_like_public_spend_query(normalized_text: str) -> bool:
    """Permite perguntas de gasto/custo quando o objeto público é reconhecível."""

    has_spend_signal = any(
        re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None
        for term in _PUBLIC_SPEND_SIGNAL_TERMS
    )
    if not has_spend_signal:
        return False

    if _extract_licitacoes_objeto(normalized_text) is not None:
        return True
    if _extract_contratos_descricao(normalized_text) is not None:
        return True
    return False


def _has_public_context_anchor(prior_user_queries: Sequence[str]) -> bool:
    """Aceita follow-up curto apenas quando ele continua uma trilha pública válida."""

    for prior_query in reversed(prior_user_queries):
        normalized_prior_query = _normalize(prior_query)
        if not normalized_prior_query:
            continue
        if _query_establishes_public_context(normalized_prior_query):
            return True
        if _looks_like_contextual_follow_up(normalized_prior_query):
            continue
        return False
    return False


def _query_establishes_public_context(normalized_text: str) -> bool:
    """Reconhece uma pergunta que por si só já estabelece escopo público."""

    if _contains_prompt_injection(normalized_text):
        return False

    strong_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_STRONG_KEYWORDS)
    weak_hits = _count_keyword_hits(normalized_text, SUPPORTED_SCOPE_WEAK_KEYWORDS)
    if strong_hits >= 1 or weak_hits >= 2:
        return True
    if _extract_nome_para_historico(normalized_text) is not None:
        return True
    return _looks_like_public_spend_query(normalized_text)


def _has_explicit_context_reference(normalized_text: str) -> bool:
    return _CONTEXTUAL_REFERENCE_PATTERN.search(normalized_text) is not None


def _has_inline_public_context_signal(
    normalized_text: str,
    *,
    strong_hits: int,
    weak_hits: int,
) -> bool:
    if strong_hits >= 1 or weak_hits >= 1:
        return True
    if _looks_like_public_spend_query(normalized_text):
        return True
    return _looks_like_short_ranking_follow_up(normalized_text)


def _looks_like_short_public_filter_follow_up(normalized_text: str) -> bool:
    tokens = _tokenize(normalized_text)
    if not tokens or len(tokens) > 8:
        return False
    if not _has_public_filter_hint(normalized_text):
        return False
    if len(tokens) == 1:
        return True
    return tokens[0] in _SHORT_FOLLOW_UP_CONNECTOR_TOKENS


def _looks_like_short_ranking_follow_up(normalized_text: str) -> bool:
    tokens = _tokenize(normalized_text)
    if not tokens or len(tokens) > 6:
        return False
    if not any(token in _SHORT_RANKING_TOKENS for token in tokens):
        return False
    return all(
        token in _SHORT_RANKING_TOKENS or token in _SHORT_RANKING_STOPWORDS
        for token in tokens
    )


def _has_public_filter_hint(normalized_text: str) -> bool:
    if _extract_year(normalized_text) is not None:
        return True
    if _extract_secretaria(normalized_text) is not None:
        return True
    if _extract_planejamento_entidade(normalized_text) is not None:
        return True
    if _extract_planejamento_area(normalized_text) is not None:
        return True
    if _extract_receitas_tema(normalized_text) is not None:
        return True
    if _extract_receitas_unidade(normalized_text) is not None:
        return True
    if _extract_licitacoes_objeto(normalized_text) is not None:
        return True
    if _extract_contratos_descricao(normalized_text) is not None:
        return True
    if _extract_contrato_fornecedor(normalized_text) is not None:
        return True
    return any(term in normalized_text for term in ("prefeitura", "camara"))


def _tokenize(normalized_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", normalized_text))
