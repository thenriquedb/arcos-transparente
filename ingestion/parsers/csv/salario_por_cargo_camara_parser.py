"""Parser CSV para a tabela de remuneracao de cargos da Camara Municipal."""

from __future__ import annotations

from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.servidores_camara import SalarioPorCargoCamaraInSchema
from shared.utils.text import normalize_search_text

from .shared import read_csv_text


def _parse_csv_rows(filepath: str) -> list[list[str]]:
    import csv
    from io import StringIO

    from .shared import clean_excel_csv_cell

    # Arquivo exportado pelo portal em ISO-8859-1
    text = read_csv_text(filepath)
    reader = csv.reader(StringIO(text), delimiter=";")
    return [[clean_excel_csv_cell(cell) for cell in row] for row in reader]


_EXPECTED_HEADER = ("codigo", "descricao do cargo")


class SalarioPorCargoCamaraParser:
    """Converte a tabela de remuneracao de cargos da Camara em registros canonicos."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        rows = _parse_csv_rows(filepath)
        if not rows:
            raise ValueError(f"Arquivo vazio: {filepath}")

        competencia = self._extract_competencia(rows, filepath)
        header_index = self._find_header_index(rows, filepath)

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for row in rows[header_index + 1 :]:
            cleaned = [c for c in row if c]
            if not cleaned or normalize_search_text(cleaned[0]).startswith("pronim"):
                break
            if len(cleaned) < 2:
                continue

            raw = {
                "competencia_referencia": competencia,
                "codigo": cleaned[0],
                "descricao": cleaned[1],
            }
            try:
                schema = SalarioPorCargoCamaraInSchema.model_validate(raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando linha invalida de salario_por_cargo_camara: {exc}")
                continue

            registros.append(schema.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartadas {invalidos} linhas invalidas em {filepath}")

        return registros

    @staticmethod
    def _extract_competencia(rows: list[list[str]], filepath: str) -> str:
        """Extrai a competencia (MM/YYYY) da linha de metadados 'Mes'."""
        for row in rows:
            for i, cell in enumerate(row):
                normalized = normalize_search_text(cell)
                # "Mês" normaliza para "mes" em UTF-8 correto
                if normalized == "mes" and i + 1 < len(row):
                    val = row[i + 1].strip()
                    if val and "/" in val and len(val) <= 8:
                        return val
        raise ValueError(f"Competencia (Mes) nao encontrada nos metadados de: {filepath}")

    @staticmethod
    def _find_header_index(rows: list[list[str]], filepath: str) -> int:
        for i, row in enumerate(rows):
            non_empty = [c for c in row if c]
            if len(non_empty) >= 2 and normalize_search_text(non_empty[0]) == "codigo":
                return i
        raise ValueError(f"Cabecalho de salario_por_cargo_camara nao encontrado em: {filepath}")
