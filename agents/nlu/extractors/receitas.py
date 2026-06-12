"""Extração de tema e unidade no domínio de receitas."""

from __future__ import annotations


RECEITAS_TEMA_ALIASES = (
    "iptu",
    "issqn",
    "iss",
    "itbi",
    "ipva",
    "fundeb",
    "enfermagem",
    "coleta de lixo",
    "taxa de servicos",
    "taxas",
)


def _extract_receitas_unidade(normalized_text: str) -> str | None:
    """Identifica a unidade responsável mais citada em perguntas de receitas."""

    if "fumusa" in normalized_text or "fundacao" in normalized_text:
        return "saude"
    if "saude" in normalized_text:
        return "saude"
    if "prefeitura" in normalized_text:
        return "prefeitura"
    return None


def _extract_receitas_tema(normalized_text: str) -> str | None:
    """Extrai temas de receitas com alto valor prático para perguntas públicas."""

    for alias in RECEITAS_TEMA_ALIASES:
        if alias in normalized_text:
            return alias
    return None
