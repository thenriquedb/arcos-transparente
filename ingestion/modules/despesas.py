"""Modulo de ingestao adapter and loaders for despesas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from database.models import (
    DespesaDocumento,
    DespesaDocumentoComprobatorio,
    DespesaDocumentoItem,
    DespesaPorFuncao,
)
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload
from shared.utils.text import normalize_search_text

from .adapters import AdapterRuntime, IngestionTypeAdapter
from .discovery import discover_despesas_files
from .shared import (
    apply_upsert_status,
    merge_load_results,
    replace_child_rows,
    upsert_by_filters,
)


def load_despesas(
    session,
    registros: list[dict[str, Any]],
    *,
    to_date,
) -> LoadResult:
    """Load despesa documents and refresh child rows on updates."""

    resultado = LoadResult()
    for registro in registros:
        registro = sanitize_xml_payload(registro)
        try:
            with session.begin():
                payload = dict(registro)
                itens = payload.pop("itens", [])
                comprovatorios = payload.pop("documentos_comprobatorios", [])
                payload["data_documento"] = to_date(payload["data_documento"])
                payload["periodo_referencia_inicio"] = to_date(payload.get("periodo_referencia_inicio"))
                payload["periodo_referencia_fim"] = to_date(payload.get("periodo_referencia_fim"))
                payload["data_homologacao"] = to_date(payload.get("data_homologacao"))
                payload["data_inicial_viagem"] = to_date(payload.get("data_inicial_viagem"))
                payload["data_final_viagem"] = to_date(payload.get("data_final_viagem"))

                documento, status = upsert_by_filters(
                    session,
                    DespesaDocumento,
                    filters=[
                        DespesaDocumento.tipo_origem == payload["tipo_origem"],
                        DespesaDocumento.arquivo_origem == payload["arquivo_origem"],
                        DespesaDocumento.sequencia_origem == payload["sequencia_origem"],
                    ],
                    payload=payload,
                )
                apply_upsert_status(resultado, status)

                replace_child_rows(
                    session,
                    DespesaDocumentoItem,
                    parent_field="documento_id",
                    parent_id=documento.id,
                    rows=[
                        {
                            "ordem": item["ordem"],
                            "numero_item": item.get("numero_item"),
                            "descricao_item": item.get("descricao_item"),
                            "quantidade": item.get("quantidade"),
                            "valor_unitario": item.get("valor_unitario"),
                            "valor_total": item.get("valor_total"),
                        }
                        for item in itens
                    ],
                )
                replace_child_rows(
                    session,
                    DespesaDocumentoComprobatorio,
                    parent_field="documento_id",
                    parent_id=documento.id,
                    rows=[
                        {
                            "ordem": comprovatorio["ordem"],
                            "data_liquidacao": to_date(comprovatorio.get("data_liquidacao")),
                            "codigo_tipo_documento": comprovatorio.get("codigo_tipo_documento"),
                            "descricao_tipo_documento": comprovatorio.get("descricao_tipo_documento"),
                            "numero_documento": comprovatorio.get("numero_documento"),
                            "serie_modelo_nota_fiscal": comprovatorio.get("serie_modelo_nota_fiscal"),
                            "descricao_serie": comprovatorio.get("descricao_serie"),
                            "chave_acesso": comprovatorio.get("chave_acesso"),
                            "data_emissao_documento": to_date(comprovatorio.get("data_emissao_documento")),
                            "valor_documento": comprovatorio.get("valor_documento"),
                            "numero_empenho": comprovatorio.get("numero_empenho"),
                            "codigo_unidade_gestora": comprovatorio.get("codigo_unidade_gestora"),
                            "numero_sequencia": comprovatorio.get("numero_sequencia"),
                        }
                        for comprovatorio in comprovatorios
                    ],
                )
        except Exception:
            session.rollback()
            resultado.erros += 1
    return resultado


def parse_despesas_csv(
    arquivo: Path,
    *,
    diarias_csv_parser,
    passagens_csv_parser,
    despesas_por_funcao_csv_parser,
) -> tuple[type, list[dict[str, Any]]]:
    """Dispatch despesas CSV inputs to the dedicated parser and target model."""

    nome = normalize_search_text(arquivo.name)
    if "diarias" in nome:
        return DespesaDocumento, diarias_csv_parser.parse(str(arquivo))
    if "passagens" in nome:
        return DespesaDocumento, passagens_csv_parser.parse(str(arquivo))
    if "despesas-por-funcao" in nome:
        return DespesaPorFuncao, despesas_por_funcao_csv_parser.parse(str(arquivo))
    raise ValueError(f"CSV de despesas sem parser suportado: {arquivo}")


def _load_files(runtime: AdapterRuntime, arquivos: list[Path]) -> LoadResult:
    resultado = LoadResult()
    for arquivo in arquivos:
        if arquivo.suffix.lower() == ".csv":
            modelo, registros = parse_despesas_csv(
                arquivo,
                diarias_csv_parser=runtime.pipeline.diarias_csv_parser,
                passagens_csv_parser=runtime.pipeline.passagens_csv_parser,
                despesas_por_funcao_csv_parser=runtime.pipeline.despesas_por_funcao_csv_parser,
            )
        else:
            modelo = DespesaDocumento
            registros = runtime.pipeline.despesas_parser.parse(str(arquivo))

        if modelo is DespesaPorFuncao:
            parcial = runtime.loader.load(registros, DespesaPorFuncao)
        else:
            parcial = load_despesas(
                runtime.session,
                registros,
                to_date=runtime.pipeline._to_date,
            )

        merge_load_results(resultado, parcial)
        runtime.emit_file_processed("despesas", arquivo)
    return resultado


ADAPTER = IngestionTypeAdapter(
    tipo="despesas",
    discover_files=discover_despesas_files,
    load_files=_load_files,
)
