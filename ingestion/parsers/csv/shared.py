"""Helpers compartilhados para leitura de CSVs."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from ingestion.parsers.xml.shared import sanitize_xml_text


CSV_FALLBACK_ENCODING = "ISO-8859-1"


def read_csv_text(filepath: str | Path, *, encoding: str = CSV_FALLBACK_ENCODING) -> str:
    """Le o CSV com encoding conhecido e remove caracteres de controle invalidos."""

    text = Path(filepath).read_text(encoding=encoding)
    return sanitize_xml_text(text) or ""


def parse_semicolon_csv_rows(filepath: str | Path) -> list[list[str]]:
    """Retorna linhas de um CSV separado por `;` com celulas saneadas."""

    text = read_csv_text(filepath)
    reader = csv.reader(StringIO(text), delimiter=";")
    return [[clean_excel_csv_cell(cell) for cell in row] for row in reader]


def clean_excel_csv_cell(value: str) -> str:
    """Remove decoracoes comuns de exports CSV do Excel/portal."""

    text = value.strip().lstrip("\ufeff")
    if not text:
        return ""
    if text.startswith("="):
        text = text[1:].lstrip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text.strip()
