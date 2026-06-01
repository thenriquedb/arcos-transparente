from __future__ import annotations

import sys

import cli
from agents.rag.indexing import KnowledgeIndexError, KnowledgeIndexStatus
from ingestion.loaders.sql_loader import LoadResult
import pytest


def test_configure_import_logging_usa_erro_por_padrao(monkeypatch) -> None:
    chamadas: list[tuple[str, object, dict[str, object]]] = []

    monkeypatch.setattr(
        cli.logger,
        "remove",
        lambda *args, **kwargs: chamadas.append(("remove", None, {})),
    )
    monkeypatch.setattr(
        cli.logger,
        "add",
        lambda sink, **kwargs: chamadas.append(("add", sink, kwargs)) or 1,
    )

    cli._configure_import_logging(verbose=False)

    assert chamadas == [
        ("remove", None, {}),
        ("add", sys.stderr, {"level": "ERROR"}),
    ]


def test_configure_import_logging_usa_info_em_modo_verbose(monkeypatch) -> None:
    chamadas: list[tuple[str, object, dict[str, object]]] = []

    monkeypatch.setattr(
        cli.logger,
        "remove",
        lambda *args, **kwargs: chamadas.append(("remove", None, {})),
    )
    monkeypatch.setattr(
        cli.logger,
        "add",
        lambda sink, **kwargs: chamadas.append(("add", sink, kwargs)) or 1,
    )

    cli._configure_import_logging(verbose=True)

    assert chamadas == [
        ("remove", None, {}),
        ("add", sys.stderr, {"level": "INFO"}),
    ]


def test_importar_configura_logging_verbose_e_emite_resumo(monkeypatch) -> None:
    class FakeProgress:
        def __enter__(self) -> FakeProgress:
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def add_task(self, *_args, **_kwargs) -> int:
            return 1

        def advance(self, *_args, **_kwargs) -> None:
            return None

    class FakePipeline:
        def __init__(self, data_dir: str) -> None:
            self.data_dir = data_dir

        def _arquivos_por_tipo(self, _tipo: str, _ano: int | None) -> list[str]:
            return ["arquivo.xml"]

        def run(self, tipos, ano, on_file_processed):
            on_file_processed("servidores", "arquivo.xml")
            return {
                "servidores": LoadResult(
                    inseridos=2,
                    atualizados=1,
                    ignorados=0,
                    erros=0,
                )
            }

    configuracoes: list[bool] = []
    impressoes: list[str] = []

    monkeypatch.setattr(cli, "IngestionPipeline", FakePipeline)
    monkeypatch.setattr(cli, "Progress", FakeProgress)
    monkeypatch.setattr(cli, "_recriar_base_importacao", lambda: None)
    monkeypatch.setattr(
        cli,
        "_configure_import_logging",
        lambda *, verbose: configuracoes.append(verbose),
    )
    monkeypatch.setattr(
        cli.console,
        "print",
        lambda *args, **kwargs: impressoes.append(str(args[0])),
    )

    cli.importar(tipo="servidores", ano=2025, force=False, verbose=True)

    assert configuracoes == [True]
    assert any("Base recriada com sucesso" in texto for texto in impressoes)
    assert any("Total -> inseridos=2" in texto for texto in impressoes)


def test_rag_index_emite_resumo(monkeypatch) -> None:
    impressoes: list[str] = []

    monkeypatch.setattr(
        cli,
        "build_knowledge_index",
        lambda *, rebuild: KnowledgeIndexStatus(
            state="ready",
            message="Indice pronto",
            manifest_path="vector_store/knowledge_markdown/manifest.json",
            persist_directory="vector_store/knowledge_markdown",
            collection_name="municipal_knowledge_markdown",
            total_chunks=7,
            document_count=3,
        ),
    )
    monkeypatch.setattr(
        cli.console,
        "print",
        lambda *args, **kwargs: impressoes.append(str(args[0])),
    )

    cli.rag_index(rebuild=True)

    assert any("Indice pronto" in texto for texto in impressoes)
    assert any("Chunks indexados: 7 | documentos: 3" in texto for texto in impressoes)


def test_rag_index_mostra_erro_claro(monkeypatch) -> None:
    impressoes: list[str] = []

    def _raise(*, rebuild: bool):
        raise KnowledgeIndexError("OPENAI_API_KEY nao configurada.")

    monkeypatch.setattr(cli, "build_knowledge_index", _raise)
    monkeypatch.setattr(
        cli.console,
        "print",
        lambda *args, **kwargs: impressoes.append(str(args[0])),
    )

    with pytest.raises(cli.typer.Exit) as exc_info:
        cli.rag_index(rebuild=False)

    assert exc_info.value.exit_code == 1
    assert any("OPENAI_API_KEY nao configurada." in texto for texto in impressoes)


def test_rag_status_exibe_estado_do_indice(monkeypatch) -> None:
    impressoes: list[str] = []

    monkeypatch.setattr(
        cli,
        "get_knowledge_index_status",
        lambda: KnowledgeIndexStatus(
            state="stale",
            message="Indice desatualizado",
            manifest_path="vector_store/knowledge_markdown/manifest.json",
            persist_directory="vector_store/knowledge_markdown",
            collection_name="municipal_knowledge_markdown",
            total_chunks=9,
            document_count=4,
            stale=True,
            changed_files=("telefones-uteis.md",),
        ),
    )
    monkeypatch.setattr(
        cli.console,
        "print",
        lambda *args, **kwargs: impressoes.append(str(args[0])),
    )

    cli.rag_status()

    assert any("Estado do indice RAG: stale" in texto for texto in impressoes)
    assert any("Indice desatualizado" in texto for texto in impressoes)
    assert any("telefones-uteis.md" in texto for texto in impressoes)
