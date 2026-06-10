"""Utilitarios compartilhados para busca textual."""

from __future__ import annotations

import unicodedata


def normalize_search_text(value: str | None) -> str:
    """Normaliza texto para comparacoes simples, ignorando caixa e acentos."""

    if value is None:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.lower()


def matches_text_query(value: str | None, query: str | None) -> bool:
    """Retorna True quando todos os termos da busca aparecem no texto."""

    query_terms = normalize_search_text(query).split()
    if not query_terms:
        return True

    searchable_text = normalize_search_text(value)
    return all(term in searchable_text for term in query_terms)
