"""Modulo de ingestao adapter and loader for transferencias financeiras."""

from __future__ import annotations

from database.models import EmendaParlamentar, TransferenciaFinanceiraMovimento
from ingestion.loaders.sql_loader import LoadResult, SQLLoader

from .adapters import build_pipeline_bulk_adapter
from .discovery import discover_transferencias_financeiras_files
from .shared import merge_load_results


def load_transferencias_financeiras(
    session,
    *,
    arquivos: list,
    batch_size: int,
    parser_xml,
    parser_csv,
) -> LoadResult:
    """Load transfer movements and emendas from the discovered mixed file set."""

    resultado = LoadResult()
    loader = SQLLoader(session=session, batch_size=batch_size)

    for arquivo in arquivos:
        if arquivo.suffix.lower() == ".xml":
            parcial = loader.load(
                parser_xml.parse(str(arquivo)),
                TransferenciaFinanceiraMovimento,
            )
        elif arquivo.suffix.lower() == ".csv":
            parcial = loader.load(
                parser_csv.parse(str(arquivo)),
                EmendaParlamentar,
            )
        else:
            continue
        merge_load_results(resultado, parcial)

    return resultado


ADAPTER = build_pipeline_bulk_adapter(
    "transferencias_financeiras",
    discover_files=discover_transferencias_financeiras_files,
    pipeline_method_name="_load_transferencias_financeiras",
)
