"""Modelos ORM do banco local, reexportados por dominio."""

from database.models.base import Base
from database.models.assets import Patrimonio
from database.models.bidding import (
    Fornecedor,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    VencedorLicitacao,
)
from database.models.contracts import (
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
)
from database.models.expenses import (
    DespesaDocumento,
    DespesaDocumentoComprobatorio,
    DespesaDocumentoItem,
    DespesaPorFuncao,
)
from database.models.elected import Eleito
from database.models.fleet import FrotaDespesa, FrotaVeiculo
from database.models.inventory import EstoqueMaterial, EstoqueMovimentacao
from database.models.payroll import (
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
)
from database.models.planning import PlanejamentoDespesa
from database.models.revenue import (
    ReceitaArrecadacao,
    ReceitaLancamento,
    ReceitaNatureza,
)
from database.models.server import QuadroPessoal, Servidor, ServidorCamara, SalarioPorCargoCamara
from database.models.transfers import (
    EmendaParlamentar,
    TransferenciaFinanceiraMovimento,
)

__all__ = [
    "Base",
    "Patrimonio",
    "Contrato",
    "ContratoDespesaOrcamentaria",
    "ContratoItemAdquirido",
    "DespesaDocumento",
    "DespesaDocumentoItem",
    "DespesaDocumentoComprobatorio",
    "DespesaPorFuncao",
    "Licitacao",
    "Fornecedor",
    "VencedorLicitacao",
    "InstrumentoContratual",
    "MateriaInstrumento",
    "Servidor",
    "QuadroPessoal",
    "ServidorCamara",
    "SalarioPorCargoCamara",
    "FrotaVeiculo",
    "FrotaDespesa",
    "EstoqueMaterial",
    "EstoqueMovimentacao",
    "ReceitaNatureza",
    "ReceitaArrecadacao",
    "ReceitaLancamento",
    "TransferenciaFinanceiraMovimento",
    "EmendaParlamentar",
    "FolhaServidor",
    "FolhaLotacao",
    "FolhaCargo",
    "FolhaPagamentoRegistro",
    "PlanejamentoDespesa",
    "Eleito",
]
