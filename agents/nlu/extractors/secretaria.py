"""Extração de secretaria canônica a partir do texto da pergunta."""

from __future__ import annotations

import re

from agents.nlu.constants import SECRETARIAS_CONHECIDAS


def _extract_secretaria(normalized_text: str) -> str | None:
    """Mapeia trechos do texto para uma secretaria canônica conhecida."""

    patterns = [
        r"\b(?:na|no|da|do)\b\s+(?:secretaria\s+de\s+)?((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\b(?:pela|pelo)\b\s+(?:secretaria\s+de\s+)?((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\bfuncionarios\b\s+\bda\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
        r"\btrabalham\b\s+\bna\b\s+((?:[a-z]+\s?){1,4})(?:\?|\s|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue

        # Condensa espaços antes de validar contra a lista canônica.
        candidato = " ".join(match.group(1).split())
        for secretaria in SECRETARIAS_CONHECIDAS:
            if secretaria in candidato:
                return secretaria
    return None
