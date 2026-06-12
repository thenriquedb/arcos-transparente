"""Guardrails compartilhados para perguntas cidadãs antes da execução do modelo."""

from __future__ import annotations

from collections.abc import Sequence
import re

from agents.chatbot.help_messages import build_scope_help_message
from agents.nlu.conversation import (
    looks_like_confirmation_reply,
    normalize_conversation_text,
)
from agents.rag.scope import (
    is_supported_knowledge_follow_up_fragment,
    is_supported_knowledge_query,
)
from agents.nlu.reading import QueryReading, read_query
from agents.nlu.models import GuardrailDecision

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
_ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN = re.compile(r"^(?:e\s+)?(?:(?:o|a|os|as)\s+)?(?:(?:de|do|da|em)\s+)?20\d{2}\??$")
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
        "quanto",
        "quantos",
        "quantas",
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
    has_history: bool = False,
    prior_user_queries: Sequence[str] = (),
    prior_messages: Sequence[tuple[str, str, bool]] = (),
) -> GuardrailDecision:
    """Aplica bloqueios hard-coded antes da execução do modelo."""

    normalized_text = normalize_conversation_text(query)

    if not normalized_text:
        return GuardrailDecision(
            allowed=False,
            category="empty_query",
            message=(
                "Envie uma pergunta sobre os dados públicos municipais disponíveis "
                "no sistema ou sobre o acervo municipal curado, como servidores, "
                "secretarias, salários-base, licitações, despesas, diárias, "
                "passagens, estoques e almoxarifado, frota e veículos, "
                "patrimônio, planejamento, receitas, transferências "
                "financeiras, emendas parlamentares, políticos eleitos, "
                "telefones úteis ou horários de ônibus (intermunicipais e do "
                "Tarifa Zero)."
            ),
        )

    reading = read_query(normalized_text)

    if reading.is_prompt_injection:
        return GuardrailDecision(
            allowed=False,
            category="prompt_injection",
            message=(
                "Não posso seguir pedidos para ignorar instruções, revelar prompts "
                "internos ou contornar regras do sistema. Posso ajudar apenas com "
                "consultas aos dados públicos municipais disponíveis."
            ),
        )

    strong_hits = reading.scope_strong_hits
    weak_hits = reading.scope_weak_hits

    has_public_context_anchor = (
        _has_public_context_anchor_from_messages(prior_messages)
        if prior_messages
        else _has_public_context_anchor(prior_user_queries)
    )
    contextual_follow_up = _looks_like_contextual_follow_up(reading)
    explicit_context_reference = _has_explicit_context_reference(normalized_text)

    if (
        has_history
        and explicit_context_reference
        and _has_inline_public_context_signal(
            reading,
            strong_hits=strong_hits,
            weak_hits=weak_hits,
        )
    ):
        return GuardrailDecision(allowed=True, category="allowed")

    if has_history and contextual_follow_up and has_public_context_anchor:
        return GuardrailDecision(allowed=True, category="allowed")

    if has_history and has_public_context_anchor and _looks_like_confirmation_reply(normalized_text, prior_messages):
        return GuardrailDecision(allowed=True, category="allowed")

    if strong_hits >= 1 or weak_hits >= 2:
        return GuardrailDecision(allowed=True, category="allowed")

    if _looks_like_public_spend_query(reading):
        return GuardrailDecision(allowed=True, category="allowed")

    if is_supported_knowledge_query(query):
        return GuardrailDecision(allowed=True, category="allowed")

    return GuardrailDecision(
        allowed=False,
        category="out_of_scope",
        message=build_scope_help_message(),
    )


def _looks_like_contextual_follow_up(reading: QueryReading) -> bool:
    """Permite continuação curta dependente de histórico sem forçar nova rota."""

    normalized_text = reading.normalized_text
    if _has_explicit_context_reference(normalized_text):
        return True
    if _ELLIPTICAL_YEAR_FOLLOW_UP_PATTERN.fullmatch(normalized_text) is not None:
        return True
    if _looks_like_short_public_filter_follow_up(reading):
        return True
    if _looks_like_short_ranking_follow_up(normalized_text):
        return True
    return False


def _looks_like_public_spend_query(reading: QueryReading) -> bool:
    """Permite perguntas de gasto/custo quando o objeto público é reconhecível."""

    has_spend_signal = any(
        re.search(rf"\b{re.escape(term)}\b", reading.normalized_text) is not None
        for term in _PUBLIC_SPEND_SIGNAL_TERMS
    )
    if not has_spend_signal:
        return False

    if reading.licitacoes_objeto is not None:
        return True
    if reading.contratos_descricao is not None:
        return True
    if reading.planejamento_programa is not None:
        return True
    if reading.planejamento_acao is not None:
        return True
    if reading.planejamento_fonte_recurso is not None:
        return True
    if reading.planejamento_area is not None:
        return True
    if reading.planejamento_entidade is not None:
        return True
    return False


def _has_public_context_anchor(prior_user_queries: Sequence[str]) -> bool:
    """Aceita follow-up curto apenas quando ele continua uma trilha pública válida."""

    for prior_query in reversed(prior_user_queries):
        reading = read_query(prior_query)
        if not reading.normalized_text:
            continue
        if _query_establishes_public_context(reading):
            return True
        if _looks_like_contextual_follow_up(reading):
            continue
        return False
    return False


def _has_public_context_anchor_from_messages(
    prior_messages: Sequence[tuple[str, str, bool]],
) -> bool:
    """Usa o historico completo para preservar follow-ups apos clarificacoes."""

    for role, content, guardrail_triggered in reversed(prior_messages):
        reading = read_query(content)
        if not reading.normalized_text:
            continue
        if guardrail_triggered:
            return False
        if role == "user":
            if _query_establishes_public_context(reading):
                return True
            if _looks_like_contextual_follow_up(reading):
                continue
            return False
        if _query_establishes_public_context(reading):
            return True
    return False


def _query_establishes_public_context(reading: QueryReading) -> bool:
    """Reconhece uma pergunta que por si só já estabelece escopo público."""

    if reading.is_prompt_injection:
        return False

    if reading.scope_strong_hits >= 1 or reading.scope_weak_hits >= 2:
        return True
    if reading.nome_historico is not None:
        return True
    if is_supported_knowledge_query(reading.normalized_text):
        return True
    return _looks_like_public_spend_query(reading)


def _has_explicit_context_reference(normalized_text: str) -> bool:
    return _CONTEXTUAL_REFERENCE_PATTERN.search(normalized_text) is not None


def _has_inline_public_context_signal(
    reading: QueryReading,
    *,
    strong_hits: int,
    weak_hits: int,
) -> bool:
    if strong_hits >= 1 or weak_hits >= 1:
        return True
    if _looks_like_public_spend_query(reading):
        return True
    return _looks_like_short_ranking_follow_up(reading.normalized_text)


def _looks_like_short_public_filter_follow_up(reading: QueryReading) -> bool:
    tokens = _tokenize(reading.normalized_text)
    if not tokens or len(tokens) > 8:
        return False
    if not _has_public_filter_hint(reading):
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
    return all(token in _SHORT_RANKING_TOKENS or token in _SHORT_RANKING_STOPWORDS for token in tokens)


def _looks_like_confirmation_reply(
    normalized_text: str,
    prior_messages: Sequence[tuple[str, str, bool]],
) -> bool:
    return looks_like_confirmation_reply(
        normalized_text,
        prior_messages=prior_messages,
    )


def _has_public_filter_hint(reading: QueryReading) -> bool:
    if reading.year is not None:
        return True
    if reading.secretaria is not None:
        return True
    if reading.planejamento_entidade is not None:
        return True
    if reading.planejamento_area is not None:
        return True
    if reading.planejamento_programa is not None:
        return True
    if reading.planejamento_acao is not None:
        return True
    if reading.planejamento_fonte_recurso is not None:
        return True
    if reading.receitas_tema is not None:
        return True
    if reading.receitas_unidade is not None:
        return True
    if reading.licitacoes_objeto is not None:
        return True
    if reading.contratos_descricao is not None:
        return True
    if reading.contrato_fornecedor is not None:
        return True
    normalized_text = reading.normalized_text
    if _looks_like_named_text_filter(normalized_text):
        return True
    if is_supported_knowledge_follow_up_fragment(normalized_text):
        return True
    return any(term in normalized_text for term in ("prefeitura", "camara"))


def _tokenize(normalized_text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", normalized_text))


def _looks_like_named_text_filter(normalized_text: str) -> bool:
    return (
        re.search(
            r"\b(?:do|da|de)\s+[a-z0-9]{2,}(?:\s+[a-z0-9]{2,}){1,4}\??$",
            normalized_text,
        )
        is not None
    )
