"""Indexacao markdown-first para o acervo local de conhecimento."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Callable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from .config import RagConfig, get_rag_config
from shared.runtime_config import get_env_value

_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MARKDOWN_SEPARATORS = [
    "\n## ",
    "\n### ",
    "\n#### ",
    "\n\n",
    "\n",
    ". ",
    " ",
    "",
]


class KnowledgeIndexError(RuntimeError):
    """Erro base para operacoes do indice local."""


class KnowledgeDependencyError(KnowledgeIndexError):
    """Dependencia opcional necessaria para indexacao/consulta nao disponivel."""


@dataclass(frozen=True)
class IndexedSource:
    path: str
    title: str
    sha256: str
    chunk_count: int


@dataclass(frozen=True)
class KnowledgeIndexManifest:
    version: int
    collection_name: str
    source_directory: str
    persist_directory: str
    embedding_model: str
    embedding_dimensions: int | None
    chunk_size: int
    chunk_overlap: int
    generated_at: str
    total_chunks: int
    source_files: tuple[IndexedSource, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_files"] = [asdict(source) for source in self.source_files]
        return payload


@dataclass(frozen=True)
class KnowledgeIndexStatus:
    state: str
    message: str
    manifest_path: str
    persist_directory: str
    collection_name: str
    total_chunks: int = 0
    document_count: int = 0
    stale: bool = False
    changed_files: tuple[str, ...] = ()
    missing_files: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _MarkdownSection:
    heading_path: tuple[str, ...]
    content: str


class _FallbackTextSplitter:
    """Fallback simples quando langchain-text-splitters ainda nao foi sincronizado."""

    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[Document]) -> list[Document]:
        chunks: list[Document] = []
        for document in documents:
            text = document.page_content.strip()
            if not text:
                continue
            if len(text) <= self._chunk_size:
                chunks.append(document)
                continue

            step = max(1, self._chunk_size - self._chunk_overlap)
            for start in range(0, len(text), step):
                chunk_text = text[start : start + self._chunk_size].strip()
                if not chunk_text:
                    continue
                metadata = dict(document.metadata)
                metadata["start_index"] = start
                chunks.append(Document(page_content=chunk_text, metadata=metadata))
                if start + self._chunk_size >= len(text):
                    break
        return chunks


def discover_markdown_files(config: RagConfig | None = None) -> list[Path]:
    """Lista o corpus markdown suportado pelo indice v1."""

    resolved_config = config or get_rag_config()
    source_directory = resolved_config.source_directory
    if not source_directory.exists():
        return []
    return sorted(path for path in source_directory.rglob("*.md") if path.is_file() and not path.name.startswith("."))


def build_knowledge_index(
    *,
    config: RagConfig | None = None,
    rebuild: bool = False,
    embeddings_factory: Callable[[], Embeddings] | None = None,
    vectorstore_cls: type | None = None,
) -> KnowledgeIndexStatus:
    """Constroi ou reconstrói o indice persistente de conhecimento markdown."""

    resolved_config = config or get_rag_config()

    if not rebuild and resolved_config.manifest_path.exists() and resolved_config.persist_directory.exists():
        raise KnowledgeIndexError("O indice de conhecimento ja existe. Use `rag index --rebuild` para recria-lo.")

    if rebuild and resolved_config.persist_directory.exists():
        shutil.rmtree(resolved_config.persist_directory)

    markdown_files = discover_markdown_files(resolved_config)
    documents: list[Document] = []
    source_files: list[IndexedSource] = []

    for path in markdown_files:
        file_documents, indexed_source = _build_documents_for_markdown(
            path,
            config=resolved_config,
        )
        documents.extend(file_documents)
        source_files.append(indexed_source)

    resolved_config.persist_directory.mkdir(parents=True, exist_ok=True)

    if documents:
        resolved_vectorstore_cls = vectorstore_cls or _get_chroma_class()
        embeddings = embeddings_factory() if embeddings_factory is not None else _build_embeddings(resolved_config)
        resolved_vectorstore_cls.from_documents(
            documents=documents,
            embedding=embeddings,
            ids=[str(document.metadata["chunk_id"]) for document in documents],
            collection_name=resolved_config.collection_name,
            persist_directory=str(resolved_config.persist_directory),
        )

    manifest = KnowledgeIndexManifest(
        version=1,
        collection_name=resolved_config.collection_name,
        source_directory=str(resolved_config.source_directory),
        persist_directory=str(resolved_config.persist_directory),
        embedding_model=resolved_config.embedding_model,
        embedding_dimensions=resolved_config.embedding_dimensions,
        chunk_size=resolved_config.chunk_size,
        chunk_overlap=resolved_config.chunk_overlap,
        generated_at=datetime.now(tz=UTC).isoformat(),
        total_chunks=len(documents),
        source_files=tuple(source_files),
    )
    _write_manifest(manifest, resolved_config.manifest_path)
    return get_knowledge_index_status(resolved_config)


def get_knowledge_index_status(
    config: RagConfig | None = None,
) -> KnowledgeIndexStatus:
    """Resume o estado do indice local para operadores e testes."""

    resolved_config = config or get_rag_config()
    manifest_path = resolved_config.manifest_path
    persist_directory = resolved_config.persist_directory

    if not manifest_path.exists() or not persist_directory.exists():
        return KnowledgeIndexStatus(
            state="missing",
            message=(
                "Indice de conhecimento ausente. Execute `uv run python cli.py rag index` "
                "para gerar o banco vetorial local."
            ),
            manifest_path=str(manifest_path),
            persist_directory=str(persist_directory),
            collection_name=resolved_config.collection_name,
        )

    try:
        manifest = load_knowledge_manifest(manifest_path)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        return KnowledgeIndexStatus(
            state="unavailable",
            message=f"Manifesto do indice esta ilegivel: {exc}",
            manifest_path=str(manifest_path),
            persist_directory=str(persist_directory),
            collection_name=resolved_config.collection_name,
        )

    if manifest.total_chunks <= 0:
        return KnowledgeIndexStatus(
            state="empty",
            message=(
                "Indice de conhecimento existe, mas nao possui chunks indexados. "
                "Revise o corpus markdown em `data/rag` e execute a indexacao novamente."
            ),
            manifest_path=str(manifest_path),
            persist_directory=str(persist_directory),
            collection_name=resolved_config.collection_name,
            total_chunks=0,
            document_count=len(manifest.source_files),
        )

    current_hashes = _collect_source_hashes(
        discover_markdown_files(resolved_config),
        resolved_config.source_directory,
    )
    manifest_hashes = {source.path: source.sha256 for source in manifest.source_files}
    changed_files = tuple(
        sorted(path for path, sha256 in current_hashes.items() if manifest_hashes.get(path) not in (None, sha256))
    )
    missing_files = tuple(sorted(path for path in manifest_hashes if path not in current_hashes))
    stale = bool(changed_files or missing_files)
    state = "stale" if stale else "ready"

    return KnowledgeIndexStatus(
        state=state,
        message=(
            "Indice pronto para consultas grounding no acervo markdown."
            if not stale
            else (
                "Indice de conhecimento desatualizado em relacao aos arquivos markdown. "
                "Execute `uv run python cli.py rag index --rebuild`."
            )
        ),
        manifest_path=str(manifest_path),
        persist_directory=str(persist_directory),
        collection_name=manifest.collection_name,
        total_chunks=manifest.total_chunks,
        document_count=len(manifest.source_files),
        stale=stale,
        changed_files=changed_files,
        missing_files=missing_files,
    )


def load_knowledge_manifest(path: str | Path) -> KnowledgeIndexManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    source_files = tuple(IndexedSource(**item) for item in payload["source_files"])
    return KnowledgeIndexManifest(
        version=int(payload["version"]),
        collection_name=str(payload["collection_name"]),
        source_directory=str(payload["source_directory"]),
        persist_directory=str(payload["persist_directory"]),
        embedding_model=str(payload["embedding_model"]),
        embedding_dimensions=payload.get("embedding_dimensions"),
        chunk_size=int(payload["chunk_size"]),
        chunk_overlap=int(payload["chunk_overlap"]),
        generated_at=str(payload["generated_at"]),
        total_chunks=int(payload["total_chunks"]),
        source_files=source_files,
    )


def _build_documents_for_markdown(
    path: Path,
    *,
    config: RagConfig,
) -> tuple[list[Document], IndexedSource]:
    text = path.read_text(encoding="utf-8")
    relative_path = path.relative_to(config.source_directory).as_posix()
    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    sections = _split_markdown_sections(text)
    title = _extract_document_title(path, sections)
    base_documents: list[Document] = []

    for section_index, section in enumerate(sections):
        metadata = {
            "source_path": relative_path,
            "document_title": title,
            "section_path": " > ".join(section.heading_path) if section.heading_path else "",
            "section_heading": section.heading_path[-1] if section.heading_path else "",
            "section_index": section_index,
            "source_hash": source_hash,
        }
        base_documents.append(Document(page_content=section.content, metadata=metadata))

    splitter = _build_text_splitter(config)
    split_documents = splitter.split_documents(base_documents)

    final_documents: list[Document] = []
    for chunk_index, document in enumerate(split_documents):
        page_content = document.page_content.strip()
        if not page_content:
            continue
        metadata = dict(document.metadata)
        metadata["chunk_index"] = chunk_index
        metadata["chunk_id"] = _build_chunk_id(
            relative_path=relative_path,
            section_path=metadata.get("section_path", ""),
            chunk_index=chunk_index,
            start_index=int(metadata.get("start_index", 0)),
            content=page_content,
        )
        final_documents.append(Document(page_content=page_content, metadata=metadata))

    return final_documents, IndexedSource(
        path=relative_path,
        title=title,
        sha256=source_hash,
        chunk_count=len(final_documents),
    )


def _split_markdown_sections(text: str) -> list[_MarkdownSection]:
    sections: list[_MarkdownSection] = []
    heading_stack: list[str] = []
    current_heading_path: tuple[str, ...] = ()
    current_lines: list[str] = []

    def flush() -> None:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append(
                _MarkdownSection(
                    heading_path=current_heading_path,
                    content=content,
                )
            )

    for line in text.splitlines():
        match = _HEADING_PATTERN.match(line)
        if match is not None:
            flush()
            current_lines.clear()

            level = len(match.group(1))
            title = match.group(2).strip()
            if len(heading_stack) >= level:
                del heading_stack[level - 1 :]
            while len(heading_stack) < level - 1:
                heading_stack.append("")
            heading_stack.append(title)
            current_heading_path = tuple(part for part in heading_stack if part)
            current_lines.append(line)
            continue

        current_lines.append(line)

    flush()
    return sections


def _extract_document_title(path: Path, sections: list[_MarkdownSection]) -> str:
    for section in sections:
        if section.heading_path:
            return section.heading_path[0]
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def _build_chunk_id(
    *,
    relative_path: str,
    section_path: str,
    chunk_index: int,
    start_index: int,
    content: str,
) -> str:
    fingerprint = "|".join(
        [
            relative_path,
            section_path,
            str(chunk_index),
            str(start_index),
            hashlib.sha256(content.encode("utf-8")).hexdigest(),
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _build_text_splitter(config: RagConfig):
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ModuleNotFoundError:
        return _FallbackTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        add_start_index=True,
        separators=_MARKDOWN_SEPARATORS,
    )


def _get_chroma_class():
    _prepare_chroma_runtime_environment()
    try:
        from langchain_chroma import Chroma
    except ModuleNotFoundError as exc:
        raise KnowledgeDependencyError(
            "Dependencia ausente para o banco vetorial. Rode `uv sync` para instalar "
            "`langchain-chroma` e dependencias relacionadas."
        ) from exc
    return Chroma


def _prepare_chroma_runtime_environment() -> None:
    """Aplica fallback seguro para stacks legados de protobuf/opentelemetry.

    Algumas combinações resolvidas por `chromadb` ainda trazem módulos gerados
    de OpenTelemetry incompatíveis com versões recentes de `protobuf`.
    Mantemos o fallback oficial do runtime Python puro para evitar que a CLI
    quebre em import-time até que o ambiente seja sincronizado com versões mais
    novas do exporter OTLP.
    """

    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")


def _build_embeddings(config: RagConfig) -> Embeddings:
    if not config.embedding_model:
        raise KnowledgeIndexError("RAG_EMBEDDING_MODEL deve ser informado.")
    if not get_env_value("OPENAI_API_KEY"):
        raise KnowledgeIndexError(
            "OPENAI_API_KEY nao configurada. Configure a chave antes de rodar `uv run python cli.py rag index`."
        )

    kwargs: dict[str, Any] = {"model": config.embedding_model}
    if config.embedding_dimensions is not None:
        kwargs["dimensions"] = config.embedding_dimensions
    return OpenAIEmbeddings(**kwargs)


def _write_manifest(manifest: KnowledgeIndexManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            manifest.to_dict(),
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _collect_source_hashes(
    markdown_files: list[Path],
    source_directory: Path,
) -> dict[str, str]:
    return {
        path.relative_to(source_directory).as_posix(): hashlib.sha256(
            path.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        for path in markdown_files
    }
