"""Parser CSV para o relatorio mensal de servidores da Camara Municipal."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.servidores_camara import ServidorCamaraInSchema
from shared.utils.text import normalize_search_text

from .shared import read_csv_text


def _parse_utf8_csv_rows(filepath: str) -> list[list[str]]:
    import csv
    from io import StringIO

    from .shared import clean_excel_csv_cell

    text = read_csv_text(filepath, encoding="utf-8")
    reader = csv.reader(StringIO(text), delimiter=";")
    return [[clean_excel_csv_cell(cell) for cell in row] for row in reader]


_EXPECTED_HEADER = (
    "nome",
    "matricula",
    "cargo",
    "lotacao",
    "vinculo",
    "situacao",
    "admissao",
    "salario base",
    "proventos",
    "vantagens",
    "proventos totais",
    "descontos",
    "liquido",
)

_COLUMN_MAP = {
    "nome": "nome",
    "matricula": "matricula",
    "cargo": "cargo",
    "lotacao": "lotacao",
    "vinculo": "vinculo",
    "situacao": "situacao_funcional",
    "admissao": "data_admissao",
    "salario base": "salario_base",
    "proventos": "proventos",
    "vantagens": "vantagens",
    "proventos totais": "proventos_totais",
    "descontos": "descontos",
    "liquido": "liquido",
}


class ServidoresCamaraCsvParser:
    """Converte o CSV mensal de servidores da Camara em registros canonicos."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        rows = _parse_utf8_csv_rows(filepath)
        if not rows:
            raise ValueError(f"Arquivo vazio: {filepath}")

        competencia = self._extract_competencia(rows[0], filepath)
        header_index = self._find_header_index(rows, filepath)

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for row in rows[header_index + 1 :]:
            # Use the full row (preserving empty cells for correct column positions)
            non_empty_check = [c for c in row if c]
            if not non_empty_check:
                break
            if normalize_search_text(non_empty_check[0]).startswith("pronim"):
                break
            if len(row) < len(_EXPECTED_HEADER):
                continue

            raw = {"competencia_referencia": competencia}
            for i, col_name in enumerate(_EXPECTED_HEADER):
                field = _COLUMN_MAP[col_name]
                raw[field] = row[i] if i < len(row) else None

            try:
                schema = ServidorCamaraInSchema.model_validate(raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando linha invalida de servidores_camara CSV: {exc}")
                continue

            registros.append(schema.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartadas {invalidos} linhas invalidas em {filepath}")

        return registros

    @staticmethod
    def _extract_competencia(first_row: list[str], filepath: str) -> str:
        """Extrai a competencia no formato MM/YYYY do titulo da primeira linha.

        O titulo pode conter YYYY/MM (ex: 2025/01) ou MM/YYYY (ex: 01/2025);
        ambos sao normalizados para MM/YYYY antes de retornar.
        """
        title = " ".join(c for c in first_row if c)
        parts = [p.strip() for p in title.split("-") if p.strip()]
        for part in reversed(parts):
            if "/" in part and len(part) <= 8:
                a, b = part.split("/", 1)
                if len(a) == 4:
                    # YYYY/MM → MM/YYYY
                    return f"{b}/{a}"
                return part
        raise ValueError(f"Competencia nao encontrada no titulo do arquivo: {filepath}")

    @staticmethod
    def _find_header_index(rows: list[list[str]], filepath: str) -> int:
        for i, row in enumerate(rows):
            non_empty = [c for c in row if c]
            if len(non_empty) >= len(_EXPECTED_HEADER) and normalize_search_text(non_empty[0]) == "nome":
                return i
        raise ValueError(f"Cabecalho de servidores_camara nao encontrado em: {filepath}")
