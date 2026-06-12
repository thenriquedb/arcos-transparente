"""Shared adapter runtime and builders for the ingestion pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ingestion.loaders.sql_loader import LoadResult, SQLLoader

from .shared import merge_load_results


if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from ingestion.pipeline import IngestionPipeline

DiscoverFiles = Callable[[Path, int | None], list[Path]]
FileProcessedHook = Callable[[str, Path], None]
LoadFiles = Callable[["AdapterRuntime", list[Path]], LoadResult]


@dataclass(slots=True)
class AdapterRuntime:
    """Concrete runtime dependencies passed to each modulo de ingestao adapter."""

    pipeline: IngestionPipeline
    session: Session
    loader: SQLLoader
    ano: int | None
    on_file_processed: FileProcessedHook | None = None

    def emit_file_processed(self, tipo: str, arquivo: Path) -> None:
        if self.on_file_processed is not None:
            self.on_file_processed(tipo, arquivo)


@dataclass(frozen=True, slots=True)
class IngestionTypeAdapter:
    """Small adapter per tipo de importacao, discovered from a registry."""

    tipo: str
    discover_files: DiscoverFiles
    load_files: LoadFiles

    def run(self, runtime: AdapterRuntime) -> LoadResult:
        arquivos = self.discover_files(runtime.pipeline.data_dir, runtime.ano)
        return self.load_files(runtime, arquivos)


def build_model_loader_adapter(
    tipo: str,
    *,
    discover_files: DiscoverFiles,
    parser_attr: str,
    model: type,
) -> IngestionTypeAdapter:
    """Build an adapter that parses one file at a time and delegates to SQLLoader."""

    def _load_files(runtime: AdapterRuntime, arquivos: list[Path]) -> LoadResult:
        resultado = LoadResult()
        parser = getattr(runtime.pipeline, parser_attr)
        for arquivo in arquivos:
            parcial = runtime.loader.load(parser.parse(str(arquivo)), model)
            merge_load_results(resultado, parcial)
            runtime.emit_file_processed(tipo, arquivo)
        return resultado

    return IngestionTypeAdapter(
        tipo=tipo,
        discover_files=discover_files,
        load_files=_load_files,
    )


def build_pipeline_file_loader_adapter(
    tipo: str,
    *,
    discover_files: DiscoverFiles,
    parser_attr: str,
    pipeline_method_name: str,
) -> IngestionTypeAdapter:
    """Build an adapter that parses per file then delegates to a pipeline helper."""

    def _load_files(runtime: AdapterRuntime, arquivos: list[Path]) -> LoadResult:
        resultado = LoadResult()
        parser = getattr(runtime.pipeline, parser_attr)
        load_method = getattr(runtime.pipeline, pipeline_method_name)
        for arquivo in arquivos:
            parcial = load_method(
                session=runtime.session,
                registros=parser.parse(str(arquivo)),
            )
            merge_load_results(resultado, parcial)
            runtime.emit_file_processed(tipo, arquivo)
        return resultado

    return IngestionTypeAdapter(
        tipo=tipo,
        discover_files=discover_files,
        load_files=_load_files,
    )


def build_pipeline_bulk_adapter(
    tipo: str,
    *,
    discover_files: DiscoverFiles,
    pipeline_method_name: str,
) -> IngestionTypeAdapter:
    """Build an adapter for tipos loaded in one pass across many files."""

    def _load_files(runtime: AdapterRuntime, arquivos: list[Path]) -> LoadResult:
        load_method = getattr(runtime.pipeline, pipeline_method_name)
        resultado = load_method(session=runtime.session, ano=runtime.ano)
        for arquivo in arquivos:
            runtime.emit_file_processed(tipo, arquivo)
        return resultado

    return IngestionTypeAdapter(
        tipo=tipo,
        discover_files=discover_files,
        load_files=_load_files,
    )
