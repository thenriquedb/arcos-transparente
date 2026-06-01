"""Configuracao do indice local de conhecimento municipal."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAG_SOURCE_DIRECTORY = PROJECT_ROOT / "data" / "rag"
DEFAULT_RAG_PERSIST_DIRECTORY = PROJECT_ROOT / "vector_store" / "knowledge_markdown"
DEFAULT_RAG_COLLECTION_NAME = "municipal_knowledge_markdown"
DEFAULT_RAG_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_RAG_CHUNK_SIZE = 1_000
DEFAULT_RAG_CHUNK_OVERLAP = 120
DEFAULT_RAG_RETRIEVAL_K = 4
DEFAULT_RAG_RELEVANCE_THRESHOLD = 0.2


@dataclass(frozen=True)
class RagConfig:
    source_directory: Path
    persist_directory: Path
    collection_name: str
    manifest_path: Path
    embedding_model: str
    embedding_dimensions: int | None
    chunk_size: int
    chunk_overlap: int
    retrieval_k: int
    relevance_threshold: float


def get_rag_config() -> RagConfig:
    source_directory = _resolve_project_path(
        os.getenv("RAG_SOURCE_DIRECTORY"),
        DEFAULT_RAG_SOURCE_DIRECTORY,
    )
    persist_directory = _resolve_project_path(
        os.getenv("RAG_PERSIST_DIRECTORY"),
        DEFAULT_RAG_PERSIST_DIRECTORY,
    )
    collection_name = (
        os.getenv("RAG_COLLECTION_NAME") or DEFAULT_RAG_COLLECTION_NAME
    ).strip()
    manifest_path = persist_directory / "manifest.json"

    return RagConfig(
        source_directory=source_directory,
        persist_directory=persist_directory,
        collection_name=collection_name or DEFAULT_RAG_COLLECTION_NAME,
        manifest_path=manifest_path,
        embedding_model=(
            os.getenv("RAG_EMBEDDING_MODEL") or DEFAULT_RAG_EMBEDDING_MODEL
        ).strip(),
        embedding_dimensions=_parse_optional_int(os.getenv("RAG_EMBEDDING_DIMENSIONS")),
        chunk_size=_parse_positive_int(
            os.getenv("RAG_CHUNK_SIZE"),
            DEFAULT_RAG_CHUNK_SIZE,
        ),
        chunk_overlap=_parse_non_negative_int(
            os.getenv("RAG_CHUNK_OVERLAP"),
            DEFAULT_RAG_CHUNK_OVERLAP,
        ),
        retrieval_k=_parse_positive_int(
            os.getenv("RAG_RETRIEVAL_K"),
            DEFAULT_RAG_RETRIEVAL_K,
        ),
        relevance_threshold=_parse_float_between_zero_and_one(
            os.getenv("RAG_RELEVANCE_THRESHOLD"),
            DEFAULT_RAG_RELEVANCE_THRESHOLD,
        ),
    )


def _resolve_project_path(value: str | None, default: Path) -> Path:
    candidate = Path(value).expanduser() if value else default
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _parse_positive_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    parsed = int(value)
    return parsed if parsed > 0 else default


def _parse_non_negative_int(value: str | None, default: int) -> int:
    if value is None or not value.strip():
        return default
    parsed = int(value)
    return parsed if parsed >= 0 else default


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _parse_float_between_zero_and_one(value: str | None, default: float) -> float:
    if value is None or not value.strip():
        return default
    parsed = float(value)
    if 0 <= parsed <= 1:
        return parsed
    return default
