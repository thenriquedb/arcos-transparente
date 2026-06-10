"""Heuristicas deterministicas para admitir perguntas do acervo markdown."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

from shared.utils.text import normalize_search_text

from .config import RagConfig, get_rag_config
from .indexing import discover_markdown_files

_QUERY_HINT_TERMS = frozenset(
    {
        "telefone",
        "telefones",
        "email",
        "e-mail",
        "contato",
        "contatos",
        "endereco",
        "enderecos",
        "horario",
        "horarios",
        "onibus",
        "rodoviario",
        "transporte",
        "estrutura",
        "organizacional",
        "ouvidoria",
        "competencia",
        "competencias",
        "reuniao",
        "reunioes",
        "comissao",
        "comissoes",
        "camara",
        "legislativo",
        "papel",
        "prefeitura",
        "servicos",
        "servico",
    }
)
_QUERY_HINT_PHRASES = (
    "como posso",
    "onde encontro",
    "o que e",
    "qual o papel",
    "quais sao as",
)
_STOPWORDS = frozenset(
    {
        "a",
        "ao",
        "aos",
        "as",
        "com",
        "como",
        "da",
        "das",
        "de",
        "do",
        "dos",
        "e",
        "em",
        "na",
        "nas",
        "no",
        "nos",
        "o",
        "os",
        "ou",
        "para",
        "por",
        "qual",
        "quais",
        "que",
        "um",
        "uma",
    }
)


@dataclass(frozen=True)
class _ScopeEntry:
    source_path: str
    searchable_text: str
    searchable_terms: frozenset[str]


def is_supported_knowledge_query(
    query: str,
    *,
    config: RagConfig | None = None,
) -> bool:
    normalized_query = normalize_search_text(query).strip()
    if not normalized_query:
        return False

    query_terms = _significant_terms(normalized_query)
    if not query_terms:
        return False

    has_hint = _has_query_hint(normalized_query)
    best_overlap = 0
    for entry in _load_scope_entries(str((config or get_rag_config()).source_directory)):
        overlap = sum(1 for token in query_terms if _entry_matches_term(entry, token))
        if overlap > best_overlap:
            best_overlap = overlap
        if overlap >= 3:
            return True

    return has_hint and best_overlap >= 2


def is_supported_knowledge_follow_up_fragment(
    query: str,
    *,
    config: RagConfig | None = None,
) -> bool:
    """Reconhece fragmentos curtos do acervo quando o contexto anterior ja e valido."""

    normalized_query = normalize_search_text(query).strip()
    if not normalized_query:
        return False

    query_terms = _significant_terms(normalized_query)
    if not query_terms:
        return False

    if _has_query_hint(normalized_query):
        return True

    for entry in _load_scope_entries(str((config or get_rag_config()).source_directory)):
        if any(_entry_matches_term(entry, token) for token in query_terms):
            return True

    return False


def clear_scope_cache() -> None:
    _load_scope_entries.cache_clear()


@lru_cache(maxsize=8)
def _load_scope_entries(source_directory: str) -> tuple[_ScopeEntry, ...]:
    resolved_config = get_rag_config()
    config = RagConfig(
        source_directory=Path(source_directory),
        persist_directory=resolved_config.persist_directory,
        collection_name=resolved_config.collection_name,
        manifest_path=resolved_config.manifest_path,
        embedding_model=resolved_config.embedding_model,
        embedding_dimensions=resolved_config.embedding_dimensions,
        chunk_size=resolved_config.chunk_size,
        chunk_overlap=resolved_config.chunk_overlap,
        retrieval_k=resolved_config.retrieval_k,
        relevance_threshold=resolved_config.relevance_threshold,
    )
    entries: list[_ScopeEntry] = []
    for path in discover_markdown_files(config):
        normalized_text = normalize_search_text(path.read_text(encoding="utf-8"))
        if not normalized_text.strip():
            continue
        entries.append(
            _ScopeEntry(
                source_path=path.relative_to(config.source_directory).as_posix(),
                searchable_text=normalized_text,
                searchable_terms=frozenset(_tokenize(normalized_text)),
            )
        )
    return tuple(entries)


def _significant_terms(normalized_query: str) -> tuple[str, ...]:
    return tuple(token for token in _tokenize(normalized_query) if len(token) >= 4 and token not in _STOPWORDS)


def _has_query_hint(normalized_query: str) -> bool:
    if any(hint in normalized_query for hint in _QUERY_HINT_PHRASES):
        return True
    return any(term in _tokenize(normalized_query) for term in _QUERY_HINT_TERMS)


def _entry_matches_term(entry: _ScopeEntry, token: str) -> bool:
    return token in entry.searchable_terms or token in entry.searchable_text


def _tokenize(normalized_query: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9-]+", normalized_query))
