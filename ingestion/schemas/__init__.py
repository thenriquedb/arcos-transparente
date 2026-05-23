"""Schemas de validacao da ingestao."""

from .licitacoes import (
    InstrumentoContratualInSchema,
    LicitacaoInSchema,
    MateriaInstrumentoInSchema,
    VencedorInSchema,
)

__all__ = [
    "LicitacaoInSchema",
    "VencedorInSchema",
    "InstrumentoContratualInSchema",
    "MateriaInstrumentoInSchema",
]
