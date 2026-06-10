"""Parser base para relatorios CSV consolidados por beneficiario.

Diarias e passagens compartilham o mesmo layout de relatorio do portal
(metadata em pares chave/valor, cabecalho fixo de sete colunas, rodape
"pronim"). Cada tipo de importacao fornece apenas rotulos e defaults; a
mecanica de leitura vive uma unica vez aqui.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.despesas import DespesaDocumentoInSchema
from shared.utils.text import normalize_search_text
from shared.utils.validation import parse_date

from .shared import parse_semicolon_csv_rows


_EXPECTED_HEADER = (
    "nome",
    "cnpj/cpf",
    "valor empenhado",
    "valor em liquidacao",
    "valor liquidado",
    "valor pago",
    "valor anulado",
)


class BeneficiarioReportCsvParser:
    """Converte relatorios consolidados por beneficiario em registros de despesa.

    Subclasses definem `tipo_origem`, `documento_prefix`, `report_label`,
    `default_categoria`/`default_descricao` e as chaves de metadata que podem
    fornecer a categoria do documento.
    """

    tipo_origem: str
    documento_prefix: str
    report_label: str
    default_categoria: str
    default_descricao: str
    categoria_metadata_keys: tuple[str, ...] = ("tipo de despesa",)

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Le o CSV e devolve registros canonicos validados de despesa."""

        rows = parse_semicolon_csv_rows(filepath)
        metadata, header_index = self._extract_metadata(rows, filepath)
        periodo_inicio, periodo_fim = self._parse_period(metadata.get("periodo"))
        origem = self._infer_origem(filepath, metadata.get("unidade gestora"))
        categoria = (
            next(
                (
                    metadata[key]
                    for key in self.categoria_metadata_keys
                    if metadata.get(key)
                ),
                None,
            )
            or self.default_categoria
        )
        descricao = metadata.get("descricao_relatorio") or self.default_descricao

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for sequencia, row in enumerate(
            self._iter_data_rows(rows, header_index), start=1
        ):
            payload_raw = {
                "tipo_origem": self.tipo_origem,
                "arquivo_origem": Path(filepath).name,
                "sequencia_origem": sequencia,
                "origem": origem,
                "exercicio": metadata.get("exercicio"),
                "unidade_gestora": metadata.get("unidade gestora"),
                "numero_documento": (
                    f"{self.documento_prefix}-"
                    f"{metadata.get('exercicio')}-{sequencia:05d}"
                ),
                "data_documento": periodo_fim or periodo_inicio,
                "periodo_referencia_inicio": periodo_inicio,
                "periodo_referencia_fim": periodo_fim or periodo_inicio,
                "categoria_documento": categoria,
                "credor": row[0],
                "cpf_cnpj": row[1],
                "descricao_acao": descricao,
                "valor_empenhado": row[2],
                "valor_liquidacao": row[3],
                "valor_liquidado": row[4],
                "valor_pago": row[5],
                "valor_anulado": row[6],
                "valor_total": row[5] or row[4] or row[2],
            }
            try:
                payload = DespesaDocumentoInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(
                    f"Descartando linha invalida de {self.report_label} CSV: {exc}"
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
            if len(cleaned_row) == 1:
                only_value = cleaned_row[0]
                if normalize_search_text(only_value) not in {"filtros utilizados"}:
                    metadata["descricao_relatorio"] = only_value
                continue
            if len(cleaned_row) % 2 != 0:
                continue
            for pos in range(0, len(cleaned_row), 2):
                key = normalize_search_text(cleaned_row[pos])
                value = cleaned_row[pos + 1].strip()
                if key and value:
                    metadata[key] = value

        if header_index is None:
            raise ValueError(
                f"Cabecalho de {self.report_label} CSV nao encontrado no arquivo "
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
    ) -> list[list[str]]:
        data_rows: list[list[str]] = []
        for row in rows[header_index + 1 :]:
            cleaned_row = [value for value in row if value]
            if not cleaned_row:
                continue
            if normalize_search_text(cleaned_row[0]).startswith("pronim"):
                break
            if len(cleaned_row) < len(_EXPECTED_HEADER):
                continue
            data_rows.append(cleaned_row[: len(_EXPECTED_HEADER)])
        return data_rows

    @staticmethod
    def _parse_period(periodo: str | None) -> tuple[str | None, str | None]:
        if not periodo:
            return None, None
        if " a " in periodo:
            inicio_txt, fim_txt = [
                part.strip() for part in periodo.split(" a ", maxsplit=1)
            ]
            inicio = parse_date(inicio_txt)
            fim = parse_date(fim_txt)
            return (
                inicio.isoformat() if inicio is not None else None,
                fim.isoformat() if fim is not None else None,
            )
        parsed = parse_date(periodo)
        if parsed is None:
            return None, None
        iso_value = parsed.isoformat()
        return iso_value, iso_value

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
