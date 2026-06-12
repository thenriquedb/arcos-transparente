"""Extração e detecção de intenção no domínio de contratos.

Cobre identificação do domínio, fornecedor, e os sinais que distinguem ranking
de contratos individuais de ranking agregado por dimensão (contagem).
"""

from __future__ import annotations

import re

from agents.nlu.constants import CONTRATOS_DOMAIN_KEYWORDS

from .text import _contains_any, _contains_any_term


_CONTRATOS_RANKING_DIMENSION_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "fornecedor",
        (
            "qual fornecedor",
            "quais fornecedores",
            "qual empresa",
            "quais empresas",
            "por fornecedor",
            "por fornecedores",
            "por empresa",
            "por empresas",
        ),
    ),
    (
        "secretaria",
        (
            "qual secretaria",
            "quais secretarias",
            "por secretaria",
            "por secretarias",
        ),
    ),
    (
        "categoria",
        (
            "qual categoria",
            "quais categorias",
            "por categoria",
            "por categorias",
        ),
    ),
)

_CONTRATOS_RANKING_DIMENSION_PLURAL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fornecedor", ("fornecedores", "empresas")),
    ("secretaria", ("secretarias",)),
    ("categoria", ("categorias",)),
)

_CONTRATOS_DIMENSION_COUNT_SIGNAL_PATTERNS = (
    "mais contratos",
    "mais contrato",
    "maior quantidade de contratos",
    "maior numero de contratos",
    "maiores quantidades de contratos",
    "maiores numeros de contratos",
    "quantos contratos",
    "quantas contratos",
)


def _is_contratos_query(normalized_text: str) -> bool:
    """Heurística simples para identificar perguntas sobre contratos."""

    return _contains_any(normalized_text, CONTRATOS_DOMAIN_KEYWORDS)


def _extract_contrato_fornecedor(normalized_text: str) -> str | None:
    """Extrai um nome de fornecedor em perguntas focadas em contratos."""

    if _extract_contratos_ranking_dimension(normalized_text) == "fornecedor" and _has_contratos_dimension_count_signal(
        normalized_text
    ):
        return None

    patterns = [
        r"\bfornecedor\b\s+([a-z0-9 .&/-]+?)(?=\s+\b(?:em|com)\b\s+\d{4}\b|\?|$)",
        r"\bempresa\b\s+([a-z0-9 .&/-]+?)(?=\s+\b(?:em|com)\b\s+\d{4}\b|\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        fornecedor = " ".join(match.group(1).split())
        if fornecedor:
            return fornecedor
    return None


def _extract_contratos_ranking_dimension(normalized_text: str) -> str | None:
    """Identifica quando o usuario quer agrupar contratos por uma dimensao."""

    for dimension, cues in _CONTRATOS_RANKING_DIMENSION_CUES:
        if any(cue in normalized_text for cue in cues):
            return dimension

    if not any(term in normalized_text for term in ("ranking", "top")):
        return None

    for dimension, aliases in _CONTRATOS_RANKING_DIMENSION_PLURAL_ALIASES:
        if _contains_any_term(normalized_text, aliases):
            return dimension
    return None


def _has_contratos_dimension_count_signal(normalized_text: str) -> bool:
    """Diferencia ranking por contagem de ranking de contratos individuais."""

    if any(pattern in normalized_text for pattern in _CONTRATOS_DIMENSION_COUNT_SIGNAL_PATTERNS):
        return True
    if any(term in normalized_text for term in ("valor", "media", "soma", "total")):
        return False
    return any(term in normalized_text for term in ("ranking", "top"))


def _is_contratos_dimension_count_ranking_query(normalized_text: str) -> bool:
    """Reconhece perguntas de ranking/contagem por dimensao no dominio de contratos."""

    if not _is_contratos_query(normalized_text):
        return False
    if _extract_contratos_ranking_dimension(normalized_text) is None:
        return False
    return _has_contratos_dimension_count_signal(normalized_text)
