"""Aliases de entidades do planejamento, compartilhados entre routing e tools."""

from __future__ import annotations

from shared.utils.text import normalize_search_text


PLANEJAMENTO_ENTIDADE_ALIASES = {
    "fumusa": (
        "fumusa",
        "fundacao de saude",
        "fundacao municipal de saude",
        "fundacao municipal saude",
        "fundacao municipal saude e assist",
        "fundacao m saude",
    ),
}


def extract_planejamento_entidade_alias(value: str | None) -> str | None:
    normalized_value = normalize_search_text(value)
    if not normalized_value:
        return None

    for entidade, aliases in PLANEJAMENTO_ENTIDADE_ALIASES.items():
        if any(alias in normalized_value for alias in aliases):
            return entidade
    return None


def get_planejamento_entidade_search_terms(value: str | None) -> tuple[str, ...]:
    entidade = extract_planejamento_entidade_alias(value)
    if entidade is not None:
        return PLANEJAMENTO_ENTIDADE_ALIASES[entidade]

    normalized_value = normalize_search_text(value)
    if not normalized_value:
        return ()
    return (normalized_value,)
