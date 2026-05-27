"""Schemas de validacao da ingestao."""

from .contratos import ContratoInSchema
from .despesas import (
    DespesaDocumentoComprobatorioInSchema,
    DespesaDocumentoInSchema,
    DespesaDocumentoItemInSchema,
)
from .eleitos import EleitoInSchema
from .licitacoes import (
    InstrumentoContratualInSchema,
    LicitacaoInSchema,
    MateriaInstrumentoInSchema,
    VencedorInSchema,
)
from .patrimonios import PatrimonioInSchema
from .quadro_pessoal import QuadroPessoalInSchema
from .servidores import ServidorInSchema

__all__ = [
    "ContratoInSchema",
    "DespesaDocumentoInSchema",
    "DespesaDocumentoItemInSchema",
    "DespesaDocumentoComprobatorioInSchema",
    "EleitoInSchema",
    "LicitacaoInSchema",
    "VencedorInSchema",
    "InstrumentoContratualInSchema",
    "MateriaInstrumentoInSchema",
    "PatrimonioInSchema",
    "QuadroPessoalInSchema",
    "ServidorInSchema",
]
