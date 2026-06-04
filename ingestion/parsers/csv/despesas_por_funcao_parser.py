"""Parser CSV para relatorios agregados de `despesas-por-funcao`."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.despesas_por_funcao import DespesaPorFuncaoInSchema
from shared.utils.text import normalize_search_text
from shared.utils.validation import parse_date

from .shared import parse_semicolon_csv_rows


_EXPECTED_HEADER = (
    "descricao",
    "acumulado ate o periodo - dotacao inicial",
    "acumulado ate o periodo - creditos adicionais/reducoes",
    "acumulado ate o periodo - dotacao atualizada",
    "no periodo - valor empenhado",
    "no periodo - valor em liquidacao",
    "no periodo - valor liquidado",
    "no periodo - valor pago",
)


class DespesasPorFuncaoCsvParser:
    """Converte o relatorio CSV agregado em linhas SQL-ready por funcao."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        rows = parse_semicolon_csv_rows(filepath)
        metadata, header_index = self._extract_metadata(rows, filepath)
        periodo_inicio, periodo_fim = self._parse_period(metadata.get("periodo"))
        origem = self._infer_origem(filepath, metadata.get("unidade gestora"))

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for linha_origem, row in self._iter_data_rows(rows, header_index):
            payload_raw = {
                "arquivo_origem": Path(filepath).name,
                "linha_origem": linha_origem,
                "origem": origem,
                "exercicio": metadata.get("exercicio"),
                "periodo_inicio": periodo_inicio,
                "periodo_fim": periodo_fim,
                "unidade_gestora": metadata.get("unidade gestora"),
                "funcao": row[0],
                "dotacao_inicial": row[1],
                "creditos_adicionais": row[2],
                "dotacao_atualizada": row[3],
                "valor_empenhado": row[4],
                "valor_em_liquidacao": row[5],
                "valor_liquidado": row[6],
                "valor_pago": row[7],
            }
            try:
                payload = DespesaPorFuncaoInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(
                    f"Descartando linha invalida de despesas-por-funcao CSV: {exc}"
                )
                continue
            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartadas {invalidos} linhas invalidas em {filepath}")

        return registros

    def _extract_metadata(
        self,
        rows: list[list[str]],
        filepath: str,
    ) -> tuple[dict[str, str], int]:
        metadata: dict[str, str] = {}
        header_index: int | None = None

        for index, row in enumerate(rows):
            cleaned_row = [value for value in row if value]
            if not cleaned_row:
                continue
            if self._is_header_row(cleaned_row):
                header_index = index
                break
            if len(cleaned_row) % 2 != 0:
                continue
            for pos in range(0, len(cleaned_row), 2):
                key = normalize_search_text(cleaned_row[pos])
                value = cleaned_row[pos + 1].strip()
                if key and value:
                    metadata[key] = value

        if header_index is None:
            raise ValueError(
                "Cabecalho de despesas-por-funcao CSV nao encontrado no arquivo "
                f"'{filepath}'."
            )

        for required_key in ("exercicio", "periodo", "unidade gestora"):
            if not metadata.get(required_key):
                raise ValueError(
                    f"Metadata obrigatoria '{required_key}' ausente em '{filepath}'."
                )

        return metadata, header_index

    def _iter_data_rows(
        self,
        rows: list[list[str]],
        header_index: int,
    ) -> list[tuple[int, list[str]]]:
        data_rows: list[tuple[int, list[str]]] = []
        for line_number, row in enumerate(
            rows[header_index + 1 :], start=header_index + 2
        ):
            cleaned_row = [value for value in row if value]
            if not cleaned_row:
                continue
            first_value = normalize_search_text(cleaned_row[0])
            if first_value.startswith("pronim"):
                break
            if first_value == "totais":
                continue
            if len(cleaned_row) < len(_EXPECTED_HEADER):
                continue
            data_rows.append((line_number, cleaned_row[: len(_EXPECTED_HEADER)]))
        return data_rows

    @staticmethod
    def _parse_period(periodo: str | None) -> tuple[date, date]:
        if not periodo:
            raise ValueError("Periodo obrigatorio ausente no relatorio")
        if " a " in periodo:
            inicio_txt, fim_txt = [
                part.strip() for part in periodo.split(" a ", maxsplit=1)
            ]
            inicio = parse_date(inicio_txt)
            fim = parse_date(fim_txt)
            if inicio is None or fim is None:
                raise ValueError("Periodo invalido em despesas-por-funcao")
            return inicio, fim
        parsed = parse_date(periodo)
        if parsed is None:
            raise ValueError("Periodo invalido em despesas-por-funcao")
        return parsed, parsed

    @staticmethod
    def _infer_origem(filepath: str, unidade_gestora: str | None) -> str:
        nome = normalize_search_text(Path(filepath).name)
        unidade = normalize_search_text(unidade_gestora)
        if "camara" in nome:
            return "camara"
        if "saude" in nome:
            return "saude"
        if "prefeitura" in nome:
            return "prefeitura"
        if "camara" in unidade:
            return "camara"
        if "saude" in unidade or "fumusa" in unidade:
            return "saude"
        return "prefeitura"

    @staticmethod
    def _is_header_row(row: list[str]) -> bool:
        normalized = tuple(
            normalize_search_text(value) for value in row[: len(_EXPECTED_HEADER)]
        )
        return normalized == _EXPECTED_HEADER
