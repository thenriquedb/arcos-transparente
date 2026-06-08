"""Shared conversational heuristics for public-query routing and follow-ups."""

from __future__ import annotations

from collections.abc import Sequence
import re

from shared.utils.text import normalize_search_text

CONFIRMATION_TOKENS = frozenset(
    {
        "sim",
        "isso",
        "isso mesmo",
        "exato",
        "correto",
        "confirmo",
        "confirmado",
        "pode ser",
        "pode",
    }
)
_CONFIRMATION_REPLY_PATTERN = re.compile(
    r"^(?:"
    r"sim|"
    r"isso(?:\s+mesmo)?|"
    r"exato|"
    r"correto|"
    r"confirm(?:o|ado|a|ar)?|"
    r"pode(?:\s+ser|\s+confirmar)?"
    r")$"
)
_ASSISTANT_CONFIRMATION_HINTS = (
    "voce quer",
    "voce gostaria",
    "pode ser",
    "confirma",
    "confirmar",
    "ano especifico",
    "qual periodo",
    "qual ano",
)


def normalize_conversation_text(text: str | None) -> str:
    """Normaliza texto livre para heuristicas conversacionais simples."""

    return normalize_search_text(text).strip()


def normalize_conversation_terms(text: str | None) -> str:
    """Normaliza e remove pontuacao para comparacoes por termo."""

    normalized = normalize_conversation_text(text)
    return " ".join(re.findall(r"[a-z0-9-]+", normalized))


def looks_like_confirmation_text(normalized_text: str) -> bool:
    """Reconhece respostas curtas de confirmacao ja normalizadas."""

    if not normalized_text:
        return False
    if normalized_text in CONFIRMATION_TOKENS:
        return True
    return _CONFIRMATION_REPLY_PATTERN.fullmatch(normalized_text) is not None


def looks_like_confirmation_reply(
    normalized_text: str,
    *,
    prior_messages: Sequence[tuple[str, str, bool]],
) -> bool:
    """Reconhece confirmacoes curtas depois de uma clarificacao assistida."""

    if not looks_like_confirmation_text(normalized_text):
        return False

    for role, content, guardrail_triggered in reversed(prior_messages):
        if guardrail_triggered:
            return False
        if role != "assistant":
            continue

        normalized_content = normalize_conversation_text(content)
        if not normalized_content:
            return False
        if "?" in content:
            return True
        return any(hint in normalized_content for hint in _ASSISTANT_CONFIRMATION_HINTS)

    return False
