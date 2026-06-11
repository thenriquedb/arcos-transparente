"""Retriever de conhecimento municipal baseado no indice vetorial local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Callable

from langchain_core.embeddings import Embeddings

from .config import RagConfig, get_rag_config
from .indexing import (
    KnowledgeDependencyError,
    KnowledgeIndexError,
    _extract_document_title,
    _split_markdown_sections,
    _build_embeddings,
    _get_chroma_class,
    discover_markdown_files,
    get_knowledge_index_status,
)
from shared.utils.text import normalize_search_text

_PHONE_PATTERN = re.compile(r"\(?\d{2}\)?\s*\d{4,5}-\d{4}")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\b")
_TOKEN_PATTERN = re.compile(r"[a-z0-9-]+")
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
_CONTACT_HINT_TERMS = frozenset(
    {
        "telefone",
        "telefones",
        "contato",
        "contatos",
        "email",
        "e-mail",
        "whatsapp",
    }
)
_SCHEDULE_HINT_TERMS = frozenset(
    {
        "horario",
        "horarios",
        "onibus",
        "tarifa",
        "linha",
        "linhas",
        "rodoviario",
        "partindo",
        "saida",
        "saidas",
    }
)
_GENERIC_INTENT_TERMS = (
    _CONTACT_HINT_TERMS | _SCHEDULE_HINT_TERMS | frozenset({"uteis", "util", "municipal", "prefeitura", "arcos"})
)


@dataclass(frozen=True)
class RetrievedPassage:
    titulo_documento: str
    arquivo_fonte: str
    secao: str
    pontuacao: float
    trecho: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    status: str
    pergunta: str
    mensagem: str
    fontes: tuple[RetrievedPassage, ...] = ()
    index_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "pergunta": self.pergunta,
            "mensagem": self.mensagem,
            "index_state": self.index_state,
            "fontes": [fonte.to_dict() for fonte in self.fontes],
        }


class KnowledgeRetriever:
    """Abre o indice persistido e devolve trechos relevantes com metadata."""

    def __init__(
        self,
        config: RagConfig | None = None,
        *,
        embeddings_factory: Callable[[], Embeddings] | None = None,
        vectorstore_cls: type | None = None,
    ) -> None:
        self._config = config or get_rag_config()
        self._embeddings_factory = embeddings_factory
        self._vectorstore_cls = vectorstore_cls

    def retrieve(
        self,
        query: str,
        *,
        limit: int | None = None,
    ) -> KnowledgeRetrievalResult:
        index_status = get_knowledge_index_status(self._config)
        if index_status.state in {"missing", "unavailable"}:
            return KnowledgeRetrievalResult(
                status="unavailable",
                pergunta=query,
                mensagem=index_status.message,
                index_state=index_status.state,
            )
        if index_status.state == "empty":
            return KnowledgeRetrievalResult(
                status="no_grounded_result",
                pergunta=query,
                mensagem=(
                    "O indice de conhecimento existe, mas ainda nao possui conteudo "
                    "markdown indexado para responder com grounding."
                ),
                index_state=index_status.state,
            )

        search_limit = limit or self._config.retrieval_k
        lexical_passages = self._retrieve_lexical_passages(
            query,
            limit=search_limit,
        )
        if lexical_passages:
            return KnowledgeRetrievalResult(
                status="ok",
                pergunta=query,
                mensagem=(
                    "Trechos recuperados por correspondencia lexical direta no "
                    "acervo markdown local. Cite as fontes ao redigir a resposta final."
                ),
                fontes=lexical_passages,
                index_state=index_status.state,
            )

        try:
            vectorstore = self._load_vectorstore()
        except (
            KnowledgeIndexError,
            KnowledgeDependencyError,
            OSError,
            ValueError,
        ) as exc:
            return KnowledgeRetrievalResult(
                status="unavailable",
                pergunta=query,
                mensagem=f"Nao foi possivel abrir o indice vetorial local: {exc}",
                index_state=index_status.state,
            )

        try:
            results = vectorstore.similarity_search_with_relevance_scores(
                query,
                k=search_limit,
                score_threshold=self._config.relevance_threshold,
            )
        except TypeError:
            raw_results = vectorstore.similarity_search_with_relevance_scores(
                query,
                k=search_limit,
            )
            results = [
                (document, score) for document, score in raw_results if score >= self._config.relevance_threshold
            ]

        passages = tuple(
            RetrievedPassage(
                titulo_documento=str(document.metadata.get("document_title") or "Documento sem titulo"),
                arquivo_fonte=str(document.metadata.get("source_path") or ""),
                secao=str(document.metadata.get("section_path") or ""),
                pontuacao=float(score),
                trecho=str(document.page_content),
            )
            for document, score in results
        )

        if not passages:
            return KnowledgeRetrievalResult(
                status="no_grounded_result",
                pergunta=query,
                mensagem=(
                    "Nao encontrei trechos suficientemente relevantes no acervo "
                    "markdown local para responder com grounding."
                ),
                index_state=index_status.state,
            )

        return KnowledgeRetrievalResult(
            status="ok",
            pergunta=query,
            mensagem=(
                "Trechos relevantes recuperados do acervo markdown local. Cite as fontes ao redigir a resposta final."
            ),
            fontes=passages,
            index_state=index_status.state,
        )

    def _retrieve_lexical_passages(
        self,
        query: str,
        *,
        limit: int,
    ) -> tuple[RetrievedPassage, ...]:
        normalized_query = normalize_search_text(query)
        query_tokens = _tokenize(normalized_query)
        if not query_tokens:
            return ()

        entity_terms = tuple(
            token
            for token in query_tokens
            if len(token) >= 4 and token not in _STOPWORDS and token not in _GENERIC_INTENT_TERMS
        )
        if not entity_terms:
            return ()

        if any(token in _CONTACT_HINT_TERMS for token in query_tokens):
            passages = self._find_contact_passages(entity_terms, limit=limit)
            if passages:
                return passages

        if any(token in _SCHEDULE_HINT_TERMS for token in query_tokens):
            passages = self._find_schedule_passages(entity_terms, limit=limit)
            if passages:
                return passages

        return ()

    def _find_contact_passages(
        self,
        entity_terms: tuple[str, ...],
        *,
        limit: int,
    ) -> tuple[RetrievedPassage, ...]:
        candidates: list[tuple[float, RetrievedPassage]] = []

        for path in discover_markdown_files(self._config):
            lines = path.read_text(encoding="utf-8").splitlines()
            title = _document_title_from_path(path)

            for index, line in enumerate(lines):
                normalized_line = normalize_search_text(line)
                overlap = _count_term_overlap(normalized_line, entity_terms)
                if overlap <= 0:
                    continue

                phone_index = _find_line_with_pattern(lines, index, _PHONE_PATTERN)
                email_index = _find_line_with_pattern(lines, index, _EMAIL_PATTERN)
                info_index = phone_index if phone_index is not None else email_index
                if info_index is None:
                    continue

                start = min(index, info_index)
                end = max(index, info_index)
                snippet_lines = [lines[pos].strip() for pos in range(start, end + 1)]
                snippet = "\n".join(line for line in snippet_lines if line).strip()
                if not snippet:
                    continue

                secao = _resolve_section_label(lines, index)
                score = float(overlap)
                if "telefone" in path.name:
                    score += 0.5
                if phone_index is not None:
                    score += 0.5

                candidates.append(
                    (
                        score,
                        RetrievedPassage(
                            titulo_documento=title,
                            arquivo_fonte=path.relative_to(self._config.source_directory).as_posix(),
                            secao=secao,
                            pontuacao=score,
                            trecho=snippet,
                        ),
                    )
                )

        candidates.sort(
            key=lambda item: (
                -item[0],
                len(item[1].trecho),
                item[1].arquivo_fonte,
            )
        )
        return tuple(passage for _, passage in candidates[:limit])

    def _find_schedule_passages(
        self,
        entity_terms: tuple[str, ...],
        *,
        limit: int,
    ) -> tuple[RetrievedPassage, ...]:
        candidates: list[tuple[float, RetrievedPassage]] = []

        for path in discover_markdown_files(self._config):
            lines = path.read_text(encoding="utf-8").splitlines()
            title = _document_title_from_path(path)

            for index, line in enumerate(lines):
                normalized_line = normalize_search_text(line)
                overlap = _count_term_overlap(normalized_line, entity_terms)
                if overlap <= 0:
                    continue

                schedule_lines = _collect_schedule_lines(lines, index)
                if not schedule_lines:
                    continue

                snippet = "\n".join(schedule_lines).strip()
                score = float(overlap) + 0.5
                if "onibus" in path.name or "horario" in path.name:
                    score += 0.5

                candidates.append(
                    (
                        score,
                        RetrievedPassage(
                            titulo_documento=title,
                            arquivo_fonte=path.relative_to(self._config.source_directory).as_posix(),
                            secao=_resolve_section_label(lines, index),
                            pontuacao=score,
                            trecho=snippet,
                        ),
                    )
                )

        candidates.sort(
            key=lambda item: (
                -item[0],
                len(item[1].trecho),
                item[1].arquivo_fonte,
            )
        )
        return tuple(passage for _, passage in candidates[:limit])

    def _load_vectorstore(self):
        vectorstore_cls = self._vectorstore_cls or _get_chroma_class()
        embeddings = (
            self._embeddings_factory() if self._embeddings_factory is not None else _build_embeddings(self._config)
        )
        return vectorstore_cls(
            collection_name=self._config.collection_name,
            persist_directory=str(self._config.persist_directory),
            embedding_function=embeddings,
        )


def _document_title_from_path(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    sections = _split_markdown_sections(text)
    return _extract_document_title(path, sections)


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN_PATTERN.findall(text))


def _count_term_overlap(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _find_line_with_pattern(
    lines: list[str],
    anchor_index: int,
    pattern: re.Pattern[str],
) -> int | None:
    start = max(0, anchor_index - 1)
    end = min(len(lines), anchor_index + 3)
    for index in range(start, end):
        if pattern.search(lines[index]):
            return index
    return None


def _resolve_section_label(lines: list[str], index: int) -> str:
    for current_index in range(index, -1, -1):
        current_line = lines[current_index].strip()
        if not current_line:
            continue
        if current_line.startswith("#"):
            return current_line.lstrip("#").strip()
        if current_index == index:
            return current_line
    return ""


def _collect_schedule_lines(lines: list[str], index: int) -> tuple[str, ...]:
    collected: list[str] = []
    for current_index in range(index, min(len(lines), index + 6)):
        current_line = lines[current_index].strip()
        if not current_line:
            if collected:
                break
            continue
        if current_index != index and current_line.startswith("#"):
            break
        collected.append(current_line)

    if not any(_TIME_PATTERN.search(line) for line in collected):
        return ()
    return tuple(collected)
