"""Extração de "objeto público" nominal (eventos, festivais, serviços...).

Reconhece o objeto contratual/licitatório/de gasto citado na pergunta — usado
para o fan-out de custo-de-evento e para os filtros de licitações e contratos.
"""

from __future__ import annotations

import re


# Objetos públicos curtos (eventos/shows) específicos o suficiente para acionar
# o fan-out de gasto-com-evento, mesmo quando aparecem isolados.
_EVENT_SHOW_OBJECT_TOKENS = frozenset(
    {
        "evento",
        "eventos",
        "show",
        "shows",
    }
)

_KNOWN_PUBLIC_OBJECT_ALIASES: tuple[tuple[str, str], ...] = (
    ("festival gastronomico", "festival gastronomico"),
    ("festival de gastronomia", "festival gastronomia"),
)

_GENERIC_PUBLIC_OBJECT_TOKENS = frozenset(
    {
        "evento",
        "eventos",
        "festival",
        "festivais",
        "show",
        "shows",
        "servico",
        "servicos",
        "objeto",
        "licitacao",
        "licitacoes",
        "pregao",
        "pregoes",
        "contrato",
        "contratos",
        "gasto",
        "gastos",
        "custo",
        "custos",
        "valor",
        "valores",
        "pago",
        "pagos",
    }
)

_PUBLIC_SCOPE_OBJECT_EXCLUSIONS = frozenset(
    {
        "administracao",
        "agricultura",
        "assistencia",
        "assistencia social",
        "camara",
        "cidadania",
        "cultura",
        "despesa",
        "despesas",
        "despesas por funcao",
        "diaria",
        "diarias",
        "educacao",
        "energia",
        "gestao ambiental",
        "habitacao",
        "legislativo",
        "legislativa",
        "meio ambiente",
        "passagem",
        "passagens",
        "prefeitura",
        "previdencia",
        "previdencia social",
        "programa nacional de alimentacao escolar",
        "merenda escolar",
        "relatorio de despesas por funcao",
        "saude",
        "saneamento",
        "seguranca",
        "seguranca publica",
        "setor de merenda escolar",
        "trabalho",
        "transporte",
        "urbanismo",
    }
)

_LEADING_PUBLIC_OBJECT_ARTICLES = frozenset(
    {
        "a",
        "as",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "um",
        "uma",
        "umas",
        "uns",
    }
)

_LEADING_PUBLIC_OBJECT_LABELS = frozenset({"evento", "eventos", "show", "shows"})

_PUBLIC_OBJECT_EXTRACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "licitacoes",
        re.compile(
            r"\b(?:licitac(?:ao|oes)|preg(?:ao|oes)|edital(?:is)?)\s+"
            r"(?P<prep>para|de|do|da|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "contratos",
        re.compile(
            r"\b(?:contrato|contratos|contratad[oa]s?)\s+"
            r"(?P<prep>para|de|do|da|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "spend",
        re.compile(
            r"\b(?:gastos?|gastou|custos?|custou|valor gasto|valor pago|pagos?)\s+"
            r"(?P<prep>com|de|do|da|no|na)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
    (
        "relation",
        re.compile(
            r"\b(?:relacionad[oa]s?\s+a|sobre)\s+"
            r"(?P<object>[a-z0-9][a-z0-9\s.&/-]{1,80}?)"
            r"(?=\s+\b(?:em|de|do|da)\b\s+20\d{2}\b|\?|$)"
        ),
    ),
)


def _normalize_public_object_candidate(raw_object: str) -> str | None:
    """Limpa um objeto textual antes de usá-lo como filtro público."""

    candidate = " ".join(raw_object.split()).strip(" .,-/")
    candidate = re.sub(r"\s+\b(?:em|de|do|da)\b\s+20\d{2}\b$", "", candidate).strip()
    if not candidate:
        return None

    tokens = candidate.split()
    while tokens and tokens[0] in _LEADING_PUBLIC_OBJECT_ARTICLES:
        tokens = tokens[1:]
    while len(tokens) > 1 and tokens[0] in _LEADING_PUBLIC_OBJECT_LABELS:
        tokens = tokens[1:]
        while tokens and tokens[0] in _LEADING_PUBLIC_OBJECT_ARTICLES:
            tokens = tokens[1:]

    if not tokens:
        return None

    normalized_candidate = " ".join(tokens).strip(" .,-/")
    if re.fullmatch(r"20\d{2}", normalized_candidate):
        return None
    return normalized_candidate or None


def _is_scope_or_department_object(candidate: str) -> bool:
    """Evita confundir secretaria/area publica com objeto contratual."""

    return candidate.startswith("secretaria de ") or (candidate in _PUBLIC_SCOPE_OBJECT_EXCLUSIONS)


def _is_too_generic_public_object(candidate: str) -> bool:
    """Rejeita frases vagas como `gasto` que pioram o roteamento."""

    tokens = tuple(re.findall(r"[a-z0-9]+", candidate))
    if not tokens:
        return True

    meaningful_tokens = tuple(
        token for token in tokens if token not in _LEADING_PUBLIC_OBJECT_ARTICLES and token != "e"
    )
    if not meaningful_tokens:
        return True

    # Objetos formados apenas por eventos/shows (ex.: "eventos", "shows e
    # eventos") são específicos o bastante para o fan-out de gasto-com-evento.
    if all(token in _EVENT_SHOW_OBJECT_TOKENS for token in meaningful_tokens):
        return False

    return all(token in _GENERIC_PUBLIC_OBJECT_TOKENS for token in meaningful_tokens)


def _extract_public_object_candidate(
    normalized_text: str,
    *,
    contexts: tuple[str, ...],
) -> str | None:
    """Extrai um objeto contratual nominal quando o contexto textual é forte."""

    for alias, canonical_value in _KNOWN_PUBLIC_OBJECT_ALIASES:
        if alias in normalized_text:
            return canonical_value

    for context_name, pattern in _PUBLIC_OBJECT_EXTRACTION_PATTERNS:
        if context_name not in contexts:
            continue
        match = pattern.search(normalized_text)
        if match is None:
            continue

        candidate = _normalize_public_object_candidate(match.group("object"))
        if candidate is None:
            continue
        if _is_scope_or_department_object(candidate):
            continue
        if _is_too_generic_public_object(candidate):
            continue
        return candidate

    return _extract_festival_object(normalized_text)


def _extract_festival_object(normalized_text: str) -> str | None:
    """Preserva a frase específica de festival; só o `festival` cru cai no default."""

    if "festival" not in normalized_text:
        return None

    match = re.search(r"\bfestival\b", normalized_text)
    if match is None:
        return None

    phrase_match = re.match(
        r"festival(?:\s+(?:de|do|da)\s+[a-z]+(?:\s+[a-z]+){0,2})?",
        normalized_text[match.start() :],
    )
    phrase = phrase_match.group(0) if phrase_match else "festival"
    return " ".join(phrase.split())


def _extract_licitacoes_objeto(normalized_text: str) -> str | None:
    """Extrai alguns objetos recorrentes de licitações com alto valor prático."""

    return _extract_public_object_candidate(
        normalized_text,
        contexts=("licitacoes", "spend"),
    )


def _extract_contratos_descricao(normalized_text: str) -> str | None:
    """Extrai termos de descrição de contrato para alguns eventos recorrentes."""

    return _extract_public_object_candidate(
        normalized_text,
        contexts=("contratos", "spend", "relation"),
    )
