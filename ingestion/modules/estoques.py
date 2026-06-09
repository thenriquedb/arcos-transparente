"""Modulo de ingestao adapter and loader for estoques."""

from __future__ import annotations

from typing import Any

from database.models import EstoqueMaterial, EstoqueMovimentacao
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_file_loader_adapter
from .discovery import discover_estoques_files
from .shared import apply_upsert_status, replace_child_rows, upsert_by_filters


def load_estoques(session, registros: list[dict[str, Any]]) -> LoadResult:
    """Load estoque materials and refresh movimentacoes only when they change."""

    resultado = LoadResult()
    for registro in registros:
        registro = sanitize_xml_payload(registro)
        try:
            with session.begin():
                payload = dict(registro)
                movimentacoes = payload.pop("movimentacoes", [])
                material, status = upsert_by_filters(
                    session,
                    EstoqueMaterial,
                    filters=[
                        EstoqueMaterial.origem == registro["origem"],
                        EstoqueMaterial.arquivo_origem == registro["arquivo_origem"],
                        EstoqueMaterial.sequencia_material
                        == registro["sequencia_material"],
                    ],
                    payload=payload,
                )

                movimentacoes_existentes = [
                    {
                        "sequencia_movimentacao": movimentacao.sequencia_movimentacao,
                        "data_movimento": movimentacao.data_movimento,
                        "tipo_movimento": movimentacao.tipo_movimento,
                        "unidade_gestora": movimentacao.unidade_gestora,
                        "almoxarifado": movimentacao.almoxarifado,
                        "localizacao": movimentacao.localizacao,
                        "classificacao": movimentacao.classificacao,
                        "quantidade": movimentacao.quantidade,
                        "valor_unitario": movimentacao.valor_unitario,
                        "valor_total": movimentacao.valor_total,
                        "custo_medio": movimentacao.custo_medio,
                    }
                    for movimentacao in sorted(
                        material.movimentacoes,
                        key=lambda row: row.sequencia_movimentacao,
                    )
                ]
                alterou_movimentacoes = movimentacoes_existentes != movimentacoes
                if alterou_movimentacoes:
                    replace_child_rows(
                        session,
                        EstoqueMovimentacao,
                        parent_field="material_id",
                        parent_id=material.id,
                        rows=movimentacoes,
                    )

                if status == "inserted":
                    resultado.inseridos += 1
                elif status == "updated" or alterou_movimentacoes:
                    resultado.atualizados += 1
                else:
                    resultado.ignorados += 1
        except Exception:
            session.rollback()
            resultado.erros += 1
    return resultado


ADAPTER = build_pipeline_file_loader_adapter(
    "estoques",
    discover_files=discover_estoques_files,
    parser_attr="estoques_parser",
    pipeline_method_name="_load_estoques",
)
