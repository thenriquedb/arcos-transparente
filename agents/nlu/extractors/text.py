"""Helpers genéricos de texto: contenção, ano, limite, escopo e injection.

Base reutilizada pelos demais extractors por escopo (planejamento, contratos,
etc.) e pelos detectores de domínio.
"""

from __future__ import annotations

import re

from agents.nlu.constants import PROMPT_INJECTION_PATTERNS


def _contains_any(normalized_text: str, keywords: tuple[str, ...]) -> bool:
    """Retorna True quando qualquer palavra-chave aparece no texto normalizado."""

    return any(keyword in normalized_text for keyword in keywords)


def _contains_term(normalized_text: str, term: str) -> bool:
    """Faz match por termo completo para evitar falsos positivos por substring."""

    return re.search(rf"\b{re.escape(term)}\b", normalized_text) is not None


def _contains_any_term(normalized_text: str, terms: tuple[str, ...]) -> bool:
    """Versão por termo completo de `_contains_any`."""

    return any(_contains_term(normalized_text, term) for term in terms)


def _extract_year(normalized_text: str) -> int | None:
    """Extrai anos no formato 20XX quando presentes no texto."""

    match = re.search(r"\b(20\d{2})\b", normalized_text)
    if match is None:
        return None
    return int(match.group(1))


def _extract_limit(normalized_text: str, default: int = 10) -> int:
    """Extrai limite apenas quando o número aparece em contexto de quantidade."""

    match = re.search(
        r"\b(?:top|maiores|menores|primeiro|primeiros|listar?|mostrar?|exibir?)\s+(\d{1,3})\b",
        normalized_text,
    )
    if match is None:
        return default
    return int(match.group(1))


def _contains_prompt_injection(normalized_text: str) -> bool:
    """Aplica patterns defensivos para bloquear tentativas de prompt injection."""

    return any(re.search(pattern, normalized_text) is not None for pattern in PROMPT_INJECTION_PATTERNS)


def _count_keyword_hits(normalized_text: str, keywords: tuple[str, ...]) -> int:
    """Conta quantas palavras-chave de um conjunto aparecem no texto."""

    return sum(1 for keyword in keywords if keyword in normalized_text)
