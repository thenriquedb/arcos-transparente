"""Helpers do RAG baseado em markdown para conhecimento municipal curado."""

from .config import RagConfig, get_rag_config
from .indexing import build_knowledge_index, get_knowledge_index_status
from .retrieval import KnowledgeRetriever

__all__ = [
    "RagConfig",
    "KnowledgeRetriever",
    "build_knowledge_index",
    "get_knowledge_index_status",
    "get_rag_config",
]
