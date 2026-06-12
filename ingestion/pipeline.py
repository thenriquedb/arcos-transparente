"""Pipeline de ingestao de arquivos estruturados -> SQL."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import and_, select

from database.models import FolhaServidor, Fornecedor, ReceitaNatureza
from database.session import get_session
from ingestion.loaders.sql_loader import LoadResult, SQLLoader
from ingestion.modules import (
    contratos as contratos_module,
)

from ingestion.modules import (
    estoques as estoques_module,
    folha_pagamento as folha_pagamento_module,
    despesas as despesas_module,
    frotas as frotas_module,
    licitacoes as licitacoes_module,
    receitas as receitas_module,
    transferencias_financeiras as transferencias_module,
)

from ingestion.modules.adapters import AdapterRuntime
from ingestion.modules.discovery import discover_files_for_tipo
from ingestion.modules.registry import build_adapter_registry
from ingestion.parsers.csv.despesas_por_funcao_parser import (
    DespesasPorFuncaoCsvParser,
)
from ingestion.parsers.csv.diarias_parser import DiariasCsvParser
from ingestion.parsers.csv.emendas_parlamentares_parser import (
    EmendasParlamentaresCsvParser,
)
from ingestion.parsers.csv.passagens_parser import PassagensCsvParser
from ingestion.parsers.xml.contratos_parser import ContratosParser
from ingestion.parsers.xml.despesas_parser import DespesasParser
from ingestion.parsers.xml.eleitos_parser import EleitosParser
from ingestion.parsers.xml.estoques_parser import EstoquesParser
from ingestion.parsers.xml.folha_pagamento_parser import FolhaPagamentoParser
from ingestion.parsers.xml.frotas_parser import FrotasParser
from ingestion.parsers.xml.licitacoes_parser import LicitacoesParser
from ingestion.parsers.xml.patrimonios_parser import PatrimoniosParser
from ingestion.parsers.xml.planejamentos_parser import PlanejamentosParser
from ingestion.parsers.xml.quadro_pessoal_parser import QuadroPessoalParser
from ingestion.parsers.xml.receitas_parser import ReceitasParser
from ingestion.parsers.xml.servidores_parser import ServidoresParser
from ingestion.parsers.xml.shared import sanitize_xml_payload
from ingestion.parsers.xml.transferencias_financeiras_parser import (
    TransferenciasFinanceirasParser,
)


class IngestionPipeline:
    """Orquestra parsers, modulos de ingestao e persistência no banco."""

    def __init__(self, data_dir: str = "data/xml", batch_size: int = 100) -> None:
        """Inicializa pipeline com pasta raiz de XML."""

        self.data_dir = Path(data_dir)
        self.batch_size = batch_size

        self.contratos_parser = ContratosParser()
        self.licitacoes_parser = LicitacoesParser()
        self.frotas_parser = FrotasParser()
        self.estoques_parser = EstoquesParser()
        self.servidores_parser = ServidoresParser()
        self.receitas_parser = ReceitasParser()
        self.folha_pagamento_parser = FolhaPagamentoParser()
        self.planejamentos_parser = PlanejamentosParser()
        self.despesas_parser = DespesasParser()
        self.patrimonios_parser = PatrimoniosParser()
        self.quadro_pessoal_parser = QuadroPessoalParser()
        self.eleitos_parser = EleitosParser()
        self.transferencias_financeiras_parser = TransferenciasFinanceirasParser()
        self.diarias_csv_parser = DiariasCsvParser()
        self.passagens_csv_parser = PassagensCsvParser()
        self.despesas_por_funcao_csv_parser = DespesasPorFuncaoCsvParser()
        self.emendas_parlamentares_csv_parser = EmendasParlamentaresCsvParser()

        self.tipo_adapters = build_adapter_registry()

    def run(
        self,
        tipos: list[str] | None = None,
        ano: int | None = None,
        on_file_processed: Callable[[str, Path], None] | None = None,
    ) -> dict[str, LoadResult]:
        """Executa importação com filtros por tipo e ano."""

        selecionados = tipos or list(self.tipo_adapters.keys())
        relatorio: dict[str, LoadResult] = {}

        with get_session() as session:
            loader = SQLLoader(session=session, batch_size=self.batch_size)
            runtime = AdapterRuntime(
                pipeline=self,
                session=session,
                loader=loader,
                ano=ano,
                on_file_processed=on_file_processed,
            )
            for tipo in selecionados:
                relatorio[tipo] = self.tipo_adapters[tipo].run(runtime)

        return relatorio

    def _load_contratos(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega contratos e vincula fornecedor canonico quando possivel."""

        return contratos_module.load_contratos(
            session,
            registros,
            get_or_create_fornecedor=self._get_or_create_fornecedor,
            to_date=self._to_date,
        )

    def _load_despesas(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega documentos de despesa e entidades filhas relacionadas."""

        return despesas_module.load_despesas(
            session,
            registros,
            to_date=self._to_date,
        )

    def _load_licitacoes(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega licitações e entidades filhas relacionadas."""

        return licitacoes_module.load_licitacoes(
            session,
            registros,
            get_or_create_fornecedor=self._get_or_create_fornecedor,
            to_date=self._to_date,
        )

    def _load_receitas(self, session, ano: int | None) -> LoadResult:
        """Carrega arrecadações e lançamentos de receitas."""

        return receitas_module.load_receitas(
            session,
            arquivos=self._arquivos_por_tipo("receitas", ano),
            parser=self.receitas_parser,
            batch_size=self.batch_size,
            ano=ano,
            get_or_create_natureza=self._get_or_create_natureza,
            to_date=self._to_date,
        )

    def _load_frotas(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega veículos de frota e despesas relacionadas."""

        return frotas_module.load_frotas(
            session,
            registros,
            to_date=self._to_date,
            to_datetime=self._to_datetime,
        )

    def _load_estoques(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega materiais de estoque e movimentacoes relacionadas."""

        return estoques_module.load_estoques(session, registros)

    def _load_transferencias_financeiras(
        self,
        session,
        ano: int | None,
    ) -> LoadResult:
        """Carrega movimentos de transferencias e emendas parlamentares."""

        return transferencias_module.load_transferencias_financeiras(
            session,
            arquivos=self._arquivos_por_tipo("transferencias_financeiras", ano),
            batch_size=self.batch_size,
            parser_xml=self.transferencias_financeiras_parser,
            parser_csv=self.emendas_parlamentares_csv_parser,
        )

    def _load_folha_pagamento(self, session, ano: int | None) -> LoadResult:
        """Carrega folha de pagamento em modelo dimensional."""

        return folha_pagamento_module.load_folha_pagamento(
            session,
            arquivos=self._arquivos_por_tipo("folha_pagamento", ano),
            parser=self.folha_pagamento_parser,
            get_or_create_folha_dim=self._get_or_create_folha_dim,
            get_or_create_folha_servidor=self._get_or_create_folha_servidor,
        )

    @staticmethod
    def _get_or_create_fornecedor(session, cnpj_cpf: str, nome: str) -> Fornecedor:
        """Busca fornecedor existente ou cria novo registro."""

        cnpj_cpf = sanitize_xml_payload(cnpj_cpf)
        nome = sanitize_xml_payload(nome)
        fornecedor = session.execute(
            select(Fornecedor).where(and_(Fornecedor.cnpj_cpf == cnpj_cpf, Fornecedor.nome == nome))
        ).scalar_one_or_none()
        if fornecedor is not None:
            return fornecedor

        fornecedor = Fornecedor(cnpj_cpf=cnpj_cpf, nome=nome)
        session.add(fornecedor)
        session.flush()
        return fornecedor

    @staticmethod
    def _to_date(value: str | date | None) -> date | None:
        """Converte string ISO para date quando necessário."""

        if isinstance(value, str):
            return date.fromisoformat(value)
        return value

    @staticmethod
    def _to_datetime(value: str | datetime | None) -> datetime | None:
        """Converte string ISO para datetime quando necessário."""

        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @staticmethod
    def _get_or_create_natureza(
        session,
        natureza: dict[str, Any],
    ) -> ReceitaNatureza | None:
        """Busca ou cria natureza de receita por identificação."""

        natureza = sanitize_xml_payload(natureza)
        identificacao = natureza.get("identificacao")
        if not identificacao:
            return None

        existente = session.execute(
            select(ReceitaNatureza).where(ReceitaNatureza.identificacao == identificacao)
        ).scalar_one_or_none()
        if existente is not None:
            return existente

        instancia = ReceitaNatureza(
            identificacao=identificacao,
            nome=natureza.get("nome"),
            nivel=natureza.get("nivel"),
            identificacao_superior=natureza.get("identificacao_superior"),
        )
        session.add(instancia)
        session.flush()
        return instancia

    @staticmethod
    def _get_or_create_folha_dim(session, model, nome: str | None):
        """Busca ou cria dimensão textual da folha."""

        return folha_pagamento_module.get_or_create_folha_dim(session, model, nome)

    @staticmethod
    def _get_or_create_folha_servidor(
        session,
        nome: str,
        cargo: str | None,
        lotacao: str | None,
        competencia_referencia: date,
        salario_base,
    ) -> FolhaServidor:
        """Busca ou cria o snapshot legado mantido a partir da folha."""

        return folha_pagamento_module.get_or_create_folha_servidor(
            session,
            nome=nome,
            cargo=cargo,
            lotacao=lotacao,
            competencia_referencia=competencia_referencia,
            salario_base=salario_base,
        )

    def _parse_despesas_csv(self, arquivo: Path) -> tuple[type, list[dict[str, Any]]]:
        """Despacha CSVs de despesas para o parser dedicado correto."""

        return despesas_module.parse_despesas_csv(
            arquivo,
            diarias_csv_parser=self.diarias_csv_parser,
            passagens_csv_parser=self.passagens_csv_parser,
            despesas_por_funcao_csv_parser=self.despesas_por_funcao_csv_parser,
        )

    def _arquivos_por_tipo(self, tipo: str, ano: int | None) -> list[Path]:
        """Descobre arquivos de entrada por tipo e ano."""

        return discover_files_for_tipo(self.data_dir, tipo, ano)
