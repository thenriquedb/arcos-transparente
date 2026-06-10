"""Modulo de ingestao adapter and loader for contratos."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from database.models import (
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
)
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_file_loader_adapter
from .discovery import discover_contratos_files
from .shared import apply_upsert_status, replace_child_rows, upsert_by_filters


def load_contratos(
    session,
    registros: list[dict[str, Any]],
    *,
    get_or_create_fornecedor: Callable[..., Any],
    to_date: Callable[[Any], Any],
) -> LoadResult:
    """Load contratos and refresh child collections on updates."""

    resultado = LoadResult()
    for registro in registros:
        registro = sanitize_xml_payload(registro)
        try:
            with session.begin():
                fornecedor = get_or_create_fornecedor(
                    session=session,
                    cnpj_cpf=registro["cnpj"],
                    nome=registro["fornecedor"],
                )
                payload = {
                    "numero": registro["numero"],
                    "numero_licitatorio": registro.get("numero_licitatorio"),
                    "numero_instrumento": registro.get("numero_instrumento"),
                    "tipo_instrumento_contratual": registro.get("tipo_instrumento_contratual"),
                    "fornecedor": registro["fornecedor"],
                    "cnpj": registro["cnpj"],
                    "fornecedor_id": fornecedor.id,
                    "valor": registro["valor"],
                    "data_inicio": to_date(registro["data_inicio"]),
                    "data_fim": to_date(registro.get("data_fim")),
                    "categoria": registro["categoria"],
                    "secretaria": registro["secretaria"],
                    "possui_aditivo": registro.get("possui_aditivo"),
                    "descricao": registro.get("descricao"),
                    "descricao_despesa": registro.get("descricao_despesa"),
                    "xml_original": registro.get("xml_original"),
                }
                contrato, status = upsert_by_filters(
                    session,
                    Contrato,
                    filters=[
                        Contrato.numero == payload["numero"],
                        Contrato.data_inicio == payload["data_inicio"],
                    ],
                    payload=payload,
                )
                apply_upsert_status(resultado, status)

                replace_child_rows(
                    session,
                    ContratoDespesaOrcamentaria,
                    parent_field="contrato_id",
                    parent_id=contrato.id,
                    rows=[
                        {
                            "ordem": ordem,
                            "unidade_gestora": despesa.get("unidade_gestora"),
                            "exercicio": despesa.get("exercicio"),
                            "orgao": despesa.get("orgao"),
                            "unidade": despesa.get("unidade"),
                            "departamento": despesa.get("departamento"),
                            "fonte_recurso": despesa.get("fonte_recurso"),
                            "natureza_despesa_rubrica": despesa.get("natureza_despesa_rubrica"),
                            "descricao_despesa": despesa.get("descricao_despesa"),
                            "valor_despesa": despesa.get("valor_despesa"),
                        }
                        for ordem, despesa in enumerate(
                            registro.get("despesas_orcamentarias", []),
                            start=1,
                        )
                    ],
                )
                replace_child_rows(
                    session,
                    ContratoItemAdquirido,
                    parent_field="contrato_id",
                    parent_id=contrato.id,
                    rows=[
                        {
                            "ordem": ordem,
                            "unidade_gestora": item.get("unidade_gestora"),
                            "numero_lote": item.get("numero_lote"),
                            "numero_item": item.get("numero_item"),
                            "identificacao": item.get("identificacao"),
                            "quantidade": item.get("quantidade"),
                            "valor_unitario": item.get("valor_unitario"),
                            "valor_total": item.get("valor_total"),
                        }
                        for ordem, item in enumerate(
                            registro.get("itens_adquiridos", []),
                            start=1,
                        )
                    ],
                )
        except Exception:
            session.rollback()
            resultado.erros += 1
    return resultado


ADAPTER = build_pipeline_file_loader_adapter(
    "contratos",
    discover_files=discover_contratos_files,
    parser_attr="contratos_parser",
    pipeline_method_name="_load_contratos",
)
