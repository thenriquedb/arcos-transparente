from __future__ import annotations

import os
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from agents.rag.config import RagConfig
from agents.rag.indexing import (
    _prepare_chroma_runtime_environment,
    build_knowledge_index,
    discover_markdown_files,
    get_knowledge_index_status,
    load_knowledge_manifest,
)
from agents.rag.retrieval import KnowledgeRetriever
from agents.rag.scope import (
    clear_scope_cache,
    is_supported_knowledge_follow_up_fragment,
    is_supported_knowledge_query,
)


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0]


class FakeBuildChroma:
    last_documents: list[Document] = []
    last_ids: list[str] = []

    def __init__(self, **_kwargs) -> None:
        return None

    @classmethod
    def from_documents(
        cls,
        *,
        documents: list[Document],
        embedding,
        ids: list[str],
        collection_name: str,
        persist_directory: str,
    ):
        cls.last_documents = list(documents)
        cls.last_ids = list(ids)
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True)
        (persist_path / f"{collection_name}.txt").write_text("ok", encoding="utf-8")
        return cls()


class FakeSearchChroma:
    results: list[tuple[Document, float]] = []

    def __init__(self, **_kwargs) -> None:
        return None

    def similarity_search_with_relevance_scores(
        self,
        _query: str,
        *,
        k: int = 4,
        score_threshold: float | None = None,
    ) -> list[tuple[Document, float]]:
        limited = list(self.results)[:k]
        if score_threshold is None:
            return limited
        return [
            (document, score) for document, score in limited if score >= score_threshold
        ]


class FailingSearchChroma:
    def __init__(self, **_kwargs) -> None:
        return None

    def similarity_search_with_relevance_scores(self, *_args, **_kwargs):
        raise AssertionError("A busca vetorial nao deveria ser chamada neste teste.")


def _make_config(tmp_path: Path, source_directory: Path) -> RagConfig:
    persist_directory = tmp_path / "vector_store" / "knowledge_markdown"
    return RagConfig(
        source_directory=source_directory,
        persist_directory=persist_directory,
        collection_name="teste-conhecimento",
        manifest_path=persist_directory / "manifest.json",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=None,
        chunk_size=120,
        chunk_overlap=20,
        retrieval_k=4,
        relevance_threshold=0.3,
    )


def test_discover_markdown_files_ignora_nao_markdown(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones\n", encoding="utf-8"
    )
    (source_directory / "estrutura.csv").write_text("nome,telefone\n", encoding="utf-8")
    (source_directory / "regimento.pdf").write_bytes(b"%PDF")

    config = _make_config(tmp_path, source_directory)

    arquivos = discover_markdown_files(config)

    assert [arquivo.name for arquivo in arquivos] == ["telefones-uteis.md"]


def test_build_knowledge_index_cria_manifesto_e_estado_ready(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\n## Ouvidoria\nTelefone institucional: (37) 3352-2583\n",
        encoding="utf-8",
    )
    (source_directory / "horario-de-onibus.md").write_text(
        "# Horários de Ônibus\n\n## Arcos a Formiga\n06:10\n07:00\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)

    status = build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )
    manifest = load_knowledge_manifest(config.manifest_path)

    assert status.state == "ready"
    assert status.total_chunks > 0
    assert status.document_count == 2
    assert manifest.collection_name == "teste-conhecimento"
    assert {source.path for source in manifest.source_files} == {
        "horario-de-onibus.md",
        "telefones-uteis.md",
    }
    assert FakeBuildChroma.last_documents
    assert len(FakeBuildChroma.last_documents) == len(FakeBuildChroma.last_ids)
    assert all(
        "chunk_id" in document.metadata for document in FakeBuildChroma.last_documents
    )


def test_build_knowledge_index_marca_stale_e_rebuild_atualiza(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    markdown_path = source_directory / "papel-camara.md"
    markdown_path.write_text(
        "# Câmara Municipal\n\n## Papel\nFiscalizar e legislar.\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)

    build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )
    manifest_antes = load_knowledge_manifest(config.manifest_path)

    markdown_path.write_text(
        "# Câmara Municipal\n\n## Papel\nFiscalizar, legislar e representar a população.\n",
        encoding="utf-8",
    )
    status_stale = get_knowledge_index_status(config)

    assert status_stale.state == "stale"
    assert status_stale.changed_files == ("papel-camara.md",)

    build_knowledge_index(
        config=config,
        rebuild=True,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )
    manifest_depois = load_knowledge_manifest(config.manifest_path)
    status_ready = get_knowledge_index_status(config)

    assert status_ready.state == "ready"
    assert (
        manifest_antes.source_files[0].sha256 != manifest_depois.source_files[0].sha256
    )


def test_get_knowledge_index_status_missing_e_empty(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    config = _make_config(tmp_path, source_directory)

    status_missing = get_knowledge_index_status(config)

    assert status_missing.state == "missing"

    status_empty = build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )

    assert status_empty.state == "empty"


def test_knowledge_retriever_retorna_trechos_grounded(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\n## Ouvidoria\nTelefone institucional: (37) 3352-2583\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)
    build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )

    FakeSearchChroma.results = [
        (
            Document(
                page_content="Telefone institucional: (37) 3352-2583",
                metadata={
                    "document_title": "Telefones úteis",
                    "source_path": "telefones-uteis.md",
                    "section_path": "Telefones úteis > Ouvidoria",
                },
            ),
            0.92,
        )
    ]

    result = KnowledgeRetriever(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeSearchChroma,
    ).retrieve("Qual o telefone da ouvidoria?")

    assert result.status == "ok"
    assert result.fontes[0].titulo_documento == "Telefones úteis"
    assert result.fontes[0].arquivo_fonte == "telefones-uteis.md"
    assert "3352-2583" in result.fontes[0].trecho


def test_knowledge_retriever_prioriza_match_lexical_para_telefone_exato(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\nOUVIDORIA\n(37) 3352-2583\n\nZOONOSES\n(37) 3352-2453\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)
    build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )

    result = KnowledgeRetriever(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FailingSearchChroma,
    ).retrieve("Qual o telefone da zoonose?")

    assert result.status == "ok"
    assert result.mensagem.startswith("Trechos recuperados por correspondencia lexical")
    assert result.fontes[0].arquivo_fonte == "telefones-uteis.md"
    assert result.fontes[0].secao == "ZOONOSES"
    assert "ZOONOSES" in result.fontes[0].trecho
    assert "(37) 3352-2453" in result.fontes[0].trecho


def test_knowledge_retriever_diferencia_miss_de_indice_ausente(tmp_path: Path) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\n## Ouvidoria\nTelefone institucional: (37) 3352-2583\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)
    build_knowledge_index(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeBuildChroma,
    )

    FakeSearchChroma.results = []
    retriever = KnowledgeRetriever(
        config=config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeSearchChroma,
    )
    miss = retriever.retrieve("Qual o telefone do gabinete do governador?")

    assert miss.status == "no_grounded_result"

    missing_config = _make_config(tmp_path / "sem-indice", tmp_path / "rag-ausente")
    unavailable = KnowledgeRetriever(
        config=missing_config,
        embeddings_factory=FakeEmbeddings,
        vectorstore_cls=FakeSearchChroma,
    ).retrieve("Qual o telefone da ouvidoria?")

    assert unavailable.status == "unavailable"


def test_scope_helper_reconhece_consulta_do_acervo_e_bloqueia_geral(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\n## Ouvidoria\nTelefone institucional: (37) 3352-2583\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)

    clear_scope_cache()

    assert is_supported_knowledge_query(
        "Qual o telefone da ouvidoria?",
        config=config,
    )
    assert not is_supported_knowledge_query(
        "Como implementar uma fila em Python?",
        config=config,
    )


def test_scope_helper_reconhece_fragmento_curto_de_followup_do_acervo(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "rag"
    source_directory.mkdir()
    (source_directory / "telefones-uteis.md").write_text(
        "# Telefones úteis\n\nPROCON\n(37) 3351-4044\n\nZOONOSES\n(37) 3352-2453\n",
        encoding="utf-8",
    )
    config = _make_config(tmp_path, source_directory)

    clear_scope_cache()

    assert is_supported_knowledge_follow_up_fragment("e do procon?", config=config)
    assert not is_supported_knowledge_follow_up_fragment(
        "e do python?",
        config=config,
    )


def test_prepare_chroma_runtime_environment_define_fallback(monkeypatch) -> None:
    monkeypatch.delenv("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", raising=False)

    _prepare_chroma_runtime_environment()

    assert os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] == "python"
