"""Modulo de ingestao adapter and loader for frotas."""

from __future__ import annotations

from typing import Any

from database.models import FrotaDespesa, FrotaVeiculo
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_file_loader_adapter
from .discovery import discover_frotas_files
from .shared import apply_upsert_status, replace_child_rows, upsert_by_filters


def load_frotas(
    session,
    registros: list[dict[str, Any]],
    *,
    to_date,
    to_datetime,
) -> LoadResult:
    """Load frota veiculos and replace dependent despesas when needed."""

    resultado = LoadResult()
    for registro in registros:
        registro = sanitize_xml_payload(registro)
        try:
            with session.begin():
                payload = dict(registro)
                payload["data_aquisicao"] = to_datetime(payload.get("data_aquisicao"))
                despesas = payload.pop("despesas", [])

                veiculo, status = upsert_by_filters(
                    session,
                    FrotaVeiculo,
                    filters=[
                        FrotaVeiculo.codigo_veiculo == registro["codigo_veiculo"],
                        FrotaVeiculo.placa_veiculo == registro.get("placa_veiculo"),
                    ],
                    payload=payload,
                )
                apply_upsert_status(resultado, status)

                replace_child_rows(
                    session,
                    FrotaDespesa,
                    parent_field="veiculo_id",
                    parent_id=veiculo.id,
                    rows=[
                        {
                            "descricao_evento": despesa.get("descricao_evento"),
                            "quantidade_lancamento": despesa.get(
                                "quantidade_lancamento"
                            ),
                            "valor_lancamento": despesa.get("valor_lancamento"),
                            "data_evento": to_date(despesa.get("data_evento")),
                            "tp_despesa": despesa.get("tp_despesa"),
                            "tipo_despesa": despesa.get("tipo_despesa"),
                            "total_despesa": despesa.get("total_despesa"),
                        }
                        for despesa in despesas
                    ],
                )
        except Exception:
            session.rollback()
            resultado.erros += 1
    return resultado


ADAPTER = build_pipeline_file_loader_adapter(
    "frotas",
    discover_files=discover_frotas_files,
    parser_attr="frotas_parser",
    pipeline_method_name="_load_frotas",
)
