"""Pipeline de ingestão XML -> SQL."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

from sqlalchemy import and_, select

from database.models import (
    Contrato,
    Fornecedor,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    Servidor,
    VencedorLicitacao,
)
from database.session import get_session
from ingestion.loaders.sql_loader import LoadResult, SQLLoader
from ingestion.parsers.xml.contratos_parser import ContratosParser
from ingestion.parsers.xml.licitacoes_parser import LicitacoesParser
from ingestion.parsers.xml.servidores_parser import ServidoresParser


class IngestionPipeline:
    """Orquestra parsers e persistência no banco."""

    def __init__(self, data_dir: str = "data/xml", batch_size: int = 100) -> None:
        """Inicializa pipeline com pasta raiz de XML."""
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.sources = {
            "contratos": (ContratosParser(), Contrato),
            "licitacoes": (LicitacoesParser(), Licitacao),
            "servidores": (ServidoresParser(), Servidor),
        }

    def run(
        self,
        tipos: Optional[list[str]] = None,
        ano: Optional[int] = None,
        on_file_processed: Optional[Callable[[str, Path], None]] = None,
    ) -> dict[str, LoadResult]:
        """Executa importação com filtros por tipo e ano."""
        selecionados = tipos or list(self.sources.keys())
        relatorio: dict[str, LoadResult] = {}

        with get_session() as session:
            loader = SQLLoader(session=session, batch_size=self.batch_size)
            for tipo in selecionados:
                parser, modelo = self.sources[tipo]
                arquivos = self._arquivos_por_tipo(tipo, ano)
                agregado = LoadResult()

                for arquivo in arquivos:
                    registros: list[dict[str, Any]] = parser.parse(str(arquivo))
                    if tipo == "licitacoes":
                        resultado = self._load_licitacoes(session=session, registros=registros)
                    else:
                        resultado = loader.load(registros, modelo)
                    agregado.inseridos += resultado.inseridos
                    agregado.atualizados += resultado.atualizados
                    agregado.ignorados += resultado.ignorados
                    agregado.erros += resultado.erros
                    if on_file_processed is not None:
                        on_file_processed(tipo, arquivo)

                relatorio[tipo] = agregado

        return relatorio

    def _load_licitacoes(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega licitações e entidades filhas relacionadas."""
        resultado = LoadResult()
        for registro in registros:
            try:
                with session.begin():
                    registro_base = {
                        "numero": registro["numero"],
                        "modalidade": registro["modalidade"],
                        "objeto": registro["objeto"],
                        "valor_estimado": registro["valor_estimado"],
                        "data_abertura": self._to_date(registro["data_abertura"]),
                        "situacao": registro["situacao"],
                        "secretaria": registro["secretaria"],
                    }
                    licitacao = session.execute(
                        select(Licitacao).where(
                            and_(
                                Licitacao.numero == registro_base["numero"],
                                Licitacao.data_abertura == registro_base["data_abertura"],
                            )
                        )
                    ).scalar_one_or_none()

                    if licitacao is None:
                        licitacao = Licitacao(**registro_base)
                        session.add(licitacao)
                        session.flush()
                        resultado.inseridos += 1
                    else:
                        alterou = False
                        for campo, valor in registro_base.items():
                            if getattr(licitacao, campo) != valor:
                                setattr(licitacao, campo, valor)
                                alterou = True
                        if alterou:
                            resultado.atualizados += 1
                        else:
                            resultado.ignorados += 1

                        session.query(VencedorLicitacao).filter(VencedorLicitacao.licitacao_id == licitacao.id).delete()
                        session.query(MateriaInstrumento).filter(
                            MateriaInstrumento.instrumento_id.in_(
                                select(InstrumentoContratual.id).where(InstrumentoContratual.licitacao_id == licitacao.id)
                            )
                        ).delete(synchronize_session=False)
                        session.query(InstrumentoContratual).filter(InstrumentoContratual.licitacao_id == licitacao.id).delete()

                    for vencedor in registro.get("vencedores", []):
                        fornecedor = self._get_or_create_fornecedor(
                            session=session,
                            cnpj_cpf=vencedor["cnpj_cpf"],
                            nome=vencedor["nome"],
                        )
                        session.add(
                            VencedorLicitacao(
                                licitacao_id=licitacao.id,
                                fornecedor_id=fornecedor.id if fornecedor else None,
                                cnpj_cpf=vencedor["cnpj_cpf"],
                                nome=vencedor["nome"],
                                validade_proposta=vencedor.get("validade_proposta"),
                            )
                        )

                    for instrumento in registro.get("instrumentos_contratuais", []):
                        fornecedor = None
                        if instrumento.get("cnpj_fornecedor") and instrumento.get("nome_fornecedor"):
                            fornecedor = self._get_or_create_fornecedor(
                                session=session,
                                cnpj_cpf=instrumento["cnpj_fornecedor"],
                                nome=instrumento["nome_fornecedor"],
                            )

                        instrumento_model = InstrumentoContratual(
                            licitacao_id=licitacao.id,
                            fornecedor_id=fornecedor.id if fornecedor else None,
                            numero_licitatorio=instrumento.get("numero_licitatorio"),
                            unidade_gestora=instrumento.get("unidade_gestora"),
                            tipo_instrumento_contratual=instrumento.get("tipo_instrumento_contratual"),
                            numero_instrumento=instrumento.get("numero_instrumento"),
                            tipo_contrato=instrumento.get("tipo_contrato"),
                            objeto=instrumento.get("objeto"),
                            data_emissao=self._to_date(instrumento.get("data_emissao")),
                            data_expiracao=self._to_date(instrumento.get("data_expiracao")),
                            possui_aditivo=instrumento.get("possui_aditivo"),
                            valor_instrumento_contratual=instrumento.get("valor_instrumento_contratual"),
                        )
                        session.add(instrumento_model)
                        session.flush()

                        for materia in instrumento.get("materias", []):
                            session.add(
                                MateriaInstrumento(
                                    instrumento_id=instrumento_model.id,
                                    unidade_gestora=materia.get("unidade_gestora"),
                                    numero_lote=materia.get("numero_lote"),
                                    numero_item=materia.get("numero_item"),
                                    identificacao=materia.get("identificacao"),
                                    quantidade=materia.get("quantidade"),
                                    valor_unitario=materia.get("valor_unitario"),
                                    valor_total=materia.get("valor_total"),
                                )
                            )
            except Exception:
                session.rollback()
                resultado.erros += 1
        return resultado

    @staticmethod
    def _get_or_create_fornecedor(session, cnpj_cpf: str, nome: str) -> Fornecedor:
        """Busca fornecedor existente ou cria novo registro."""
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
    def _to_date(value: Any) -> Any:
        """Converte string ISO para date quando necessário."""
        if isinstance(value, str):
            return date.fromisoformat(value)
        return value

    def _arquivos_por_tipo(self, tipo: str, ano: Optional[int]) -> list[Path]:
        """Descobre arquivos de entrada por tipo e ano."""
        arquivos = sorted(self.data_dir.rglob(f"*{tipo}*.xml"))
        if ano is None:
            return arquivos
        marcador = str(ano)
        return [arquivo for arquivo in arquivos if marcador in arquivo.name]
