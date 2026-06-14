"""Utilitarios compartilhados para busca textual."""

from __future__ import annotations

import re
import unicodedata


_PLURAL_SUFFIX_REWRITES = (
    ("oes", "ao"),
    ("aes", "ao"),
    ("ais", "al"),
    ("eis", "el"),
    ("ois", "ol"),
    ("is", "il"),
    ("ns", "m"),
)


def normalize_search_text(value: str | None) -> str:
    """Normaliza texto para comparacoes simples, ignorando caixa e acentos."""

    if value is None:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.lower()


def _tokenize_search_text(value: str | None) -> tuple[str, ...]:
    """Extrai termos alfanumericos do texto normalizado."""

    return tuple(re.findall(r"[a-z0-9]+", normalize_search_text(value)))


def _singularize_search_term(term: str) -> str:
    """Colapsa alguns plurais comuns do portugues para a forma singular."""

    for plural_suffix, singular_suffix in _PLURAL_SUFFIX_REWRITES:
        if len(term) <= len(plural_suffix) + 1 or not term.endswith(plural_suffix):
            continue
        return f"{term[: -len(plural_suffix)]}{singular_suffix}"
    return term


def matches_text_query(value: str | None, query: str | None) -> bool:
    """Retorna True quando todos os termos da busca aparecem no texto.

    Alem da correspondencia literal sem acentos/caixa, tenta alinhar plurais
    irregulares comuns do portugues, como `imoveis` -> `imovel`.
    """

    query_terms = _tokenize_search_text(query)
    if not query_terms:
        return True

    searchable_text = normalize_search_text(value)
    if all(term in searchable_text for term in query_terms):
        return True

    text_terms = {_singularize_search_term(term) for term in _tokenize_search_text(value)}
    if not text_terms:
        return False

    return all(term in searchable_text or _singularize_search_term(term) in text_terms for term in query_terms)
