"""Schemas de validacao da ingestao."""

from .contratos import ContratoInSchema
from .licitacoes import (
    InstrumentoContratualInSchema,
    LicitacaoInSchema,
    MateriaInstrumentoInSchema,
    VencedorInSchema,
)
from .servidores import ServidorInSchema

__all__ = [
    "ContratoInSchema",
    "LicitacaoInSchema",
    "VencedorInSchema",
    "InstrumentoContratualInSchema",
    "MateriaInstrumentoInSchema",
    "ServidorInSchema",
]
