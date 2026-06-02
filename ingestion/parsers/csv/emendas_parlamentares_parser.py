"""Parser CSV para emendas parlamentares."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shared.utils.text import normalize_search_text
from shared.utils.validation import parse_decimal, parse_int

from .shared import parse_semicolon_csv_rows


_EXPECTED_HEADER = (
    "ano/numero",
    "autor",
    "objeto",
    "tipo",
    "funcao",
    "valor",
)


class EmendasParlamentaresCsvParser:
    """Converte CSVs de emendas parlamentares em registros SQL-ready."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        rows = parse_semicolon_csv_rows(filepath)
        metadata = self._extract_metadata(rows, filepath)
        exercicio_consulta = parse_int(metadata.get("exercicio"))
        if exercicio_consulta is None:
            raise ValueError(
                f"Metadata obrigatoria 'exercicio' ausente em '{filepath}'."
            )

        registros: list[dict[str, Any]] = []
        arquivo_origem = Path(filepath).name
        for sequencia, row in enumerate(self._iter_data_rows(rows, filepath), start=1):
            ano_numero = self._clean_export_value(row[0])
            match = re.fullmatch(r"(\d{4})/(.+)", ano_numero)
            if match is None:
                continue
            registros.append(
                {
                    "arquivo_origem": arquivo_origem,
                    "sequencia_origem": sequencia,
                    "exercicio_consulta": exercicio_consulta,
                    "ano": int(match.group(1)),
                    "ano_numero": ano_numero,
                    "autor": self._clean_export_value(row[1]),
                    "objeto": self._clean_export_value(row[2]),
                    "tipo_emenda": self._clean_export_value(row[3]),
                    "funcao": self._clean_export_value(row[4]),
                    "valor": parse_decimal(self._clean_export_value(row[5])),
                }
            )

        return registros

    def _extract_metadata(
        self,
        rows: list[list[str]],
        filepath: str,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {}
        header_found = False

        for row in rows:
            cleaned_row = [self._clean_export_value(value) for value in row if value]
            if not cleaned_row:
                continue
            if self._is_header_row(cleaned_row):
                header_found = True
                continue
            if len(cleaned_row) == 1:
                continue
            if len(cleaned_row) % 2 != 0:
                continue
            for pos in range(0, len(cleaned_row), 2):
                key = normalize_search_text(cleaned_row[pos])
                value = cleaned_row[pos + 1].strip()
                if key and value:
                    metadata[key] = value

        if not header_found:
            raise ValueError(
                f"Cabecalho de emendas parlamentares CSV nao encontrado no arquivo '{filepath}'."
            )

        return metadata

    def _iter_data_rows(
        self,
        rows: list[list[str]],
        filepath: str,
    ) -> list[list[str]]:
        data_rows: list[list[str]] = []
        header_found = False

        for row in rows:
            cleaned_row = [self._clean_export_value(value) for value in row if value]
            if not cleaned_row:
                continue
            if self._is_header_row(cleaned_row):
                header_found = True
                continue
            if not header_found:
                continue
            if normalize_search_text(cleaned_row[0]).startswith("pronim"):
                break
            if len(cleaned_row) == 1:
                continue
            if len(cleaned_row) < len(_EXPECTED_HEADER):
                continue
            if normalize_search_text(cleaned_row[0]) == "emendas parlamentares":
                continue
            data_rows.append(cleaned_row[: len(_EXPECTED_HEADER)])

        if not header_found:
            raise ValueError(
                f"Cabecalho de emendas parlamentares CSV nao encontrado no arquivo '{filepath}'."
            )

        return data_rows

    @staticmethod
    def _is_header_row(row: list[str]) -> bool:
        normalized = tuple(
            normalize_search_text(value) for value in row[: len(_EXPECTED_HEADER)]
        )
        return normalized == _EXPECTED_HEADER

    @classmethod
    def _clean_export_value(cls, value: str) -> str:
        text = value.strip()
        previous = None
        while text and text != previous:
            previous = text
            if text.startswith("="):
                text = text[1:].lstrip()
            if len(text) >= 2 and text[0] == text[-1] == '"':
                text = text[1:-1].strip()
        return text.strip()
