"""Schemas de validacao da ingestao."""

from .licitacoes import (
    InstrumentoContratualInSchema,
    LicitacaoInSchema,
    MateriaInstrumentoInSchema,
    VencedorInSchema,
)
from .servidores import ServidorInSchema

__all__ = [
    "LicitacaoInSchema",
    "VencedorInSchema",
    "InstrumentoContratualInSchema",
    "MateriaInstrumentoInSchema",
    "ServidorInSchema",
]
