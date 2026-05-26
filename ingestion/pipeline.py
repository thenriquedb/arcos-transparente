"""Pipeline de ingestão XML -> SQL."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Optional

from sqlalchemy import and_, select

from database.models import (
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
    FrotaDespesa,
    FrotaVeiculo,
    Fornecedor,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    PlanejamentoDespesa,
    ReceitaArrecadacao,
    ReceitaLancamento,
    ReceitaNatureza,
    Servidor,
    VencedorLicitacao,
)
from database.session import get_session
from ingestion.loaders.sql_loader import LoadResult, SQLLoader
from ingestion.parsers.xml.contratos_parser import ContratosParser
from ingestion.parsers.xml.licitacoes_parser import LicitacoesParser
from ingestion.parsers.xml.frotas_parser import FrotasParser
from ingestion.parsers.xml.servidores_parser import ServidoresParser
from ingestion.parsers.xml.receitas_parser import ReceitasParser
from ingestion.parsers.xml.folha_pagamento_parser import FolhaPagamentoParser
from ingestion.parsers.xml.planejamentos_parser import PlanejamentosParser


class IngestionPipeline:
    """Orquestra parsers e persistência no banco."""

    def __init__(self, data_dir: str = "data/xml", batch_size: int = 100) -> None:
        """Inicializa pipeline com pasta raiz de XML."""
        self.data_dir = Path(data_dir)
        self.batch_size = batch_size
        self.sources = {
            "contratos": (ContratosParser(), Contrato),
            "licitacoes": (LicitacoesParser(), Licitacao),
            "frotas": (FrotasParser(), FrotaVeiculo),
            "servidores": (ServidoresParser(), Servidor),
            "receitas": (ReceitasParser(), ReceitaArrecadacao),
            "folha_pagamento": (FolhaPagamentoParser(), FolhaPagamentoRegistro),
            "planejamentos": (PlanejamentosParser(), PlanejamentoDespesa),
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

                if tipo == "receitas":
                    resultado = self._load_receitas(session=session, ano=ano)
                    agregado.inseridos += resultado.inseridos
                    agregado.atualizados += resultado.atualizados
                    agregado.ignorados += resultado.ignorados
                    agregado.erros += resultado.erros
                    if on_file_processed is not None:
                        for arquivo in arquivos:
                            on_file_processed(tipo, arquivo)
                    relatorio[tipo] = agregado
                    continue
                if tipo == "contratos":
                    for arquivo in arquivos:
                        registros = parser.parse(str(arquivo))
                        resultado_arquivo = self._load_contratos(
                            session=session,
                            registros=registros,
                        )
                        agregado.inseridos += resultado_arquivo.inseridos
                        agregado.atualizados += resultado_arquivo.atualizados
                        agregado.ignorados += resultado_arquivo.ignorados
                        agregado.erros += resultado_arquivo.erros
                        if on_file_processed is not None:
                            on_file_processed(tipo, arquivo)
                    relatorio[tipo] = agregado
                    continue
                if tipo == "folha_pagamento":
                    resultado = self._load_folha_pagamento(session=session, ano=ano)
                    agregado.inseridos += resultado.inseridos
                    agregado.atualizados += resultado.atualizados
                    agregado.ignorados += resultado.ignorados
                    agregado.erros += resultado.erros
                    if on_file_processed is not None:
                        for arquivo in arquivos:
                            on_file_processed(tipo, arquivo)
                    relatorio[tipo] = agregado
                    continue

                for arquivo in arquivos:
                    registros: list[dict[str, Any]] = parser.parse(str(arquivo))
                    if tipo == "licitacoes":
                        resultado = self._load_licitacoes(
                            session=session, registros=registros
                        )
                    elif tipo == "frotas":
                        resultado = self._load_frotas(
                            session=session, registros=registros
                        )
                    elif tipo == "receitas":
                        resultado = self._load_receitas(session=session, ano=ano)
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

    def _load_contratos(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega contratos e vincula fornecedor canonico quando possivel."""
        resultado = LoadResult()
        for registro in registros:
            try:
                with session.begin():
                    fornecedor = self._get_or_create_fornecedor(
                        session=session,
                        cnpj_cpf=registro["cnpj"],
                        nome=registro["fornecedor"],
                    )
                    payload = {
                        "numero": registro["numero"],
                        "numero_licitatorio": registro.get("numero_licitatorio"),
                        "numero_instrumento": registro.get("numero_instrumento"),
                        "tipo_instrumento_contratual": registro.get(
                            "tipo_instrumento_contratual"
                        ),
                        "fornecedor": registro["fornecedor"],
                        "cnpj": registro["cnpj"],
                        "fornecedor_id": fornecedor.id,
                        "valor": registro["valor"],
                        "data_inicio": self._to_date(registro["data_inicio"]),
                        "data_fim": self._to_date(registro.get("data_fim")),
                        "categoria": registro["categoria"],
                        "secretaria": registro["secretaria"],
                        "possui_aditivo": registro.get("possui_aditivo"),
                        "descricao": registro.get("descricao"),
                        "descricao_despesa": registro.get("descricao_despesa"),
                        "xml_original": registro.get("xml_original"),
                    }
                    existente = session.execute(
                        select(Contrato).where(
                            and_(
                                Contrato.numero == payload["numero"],
                                Contrato.data_inicio == payload["data_inicio"],
                            )
                        )
                    ).scalar_one_or_none()
                    if existente is None:
                        contrato = Contrato(**payload)
                        session.add(contrato)
                        session.flush()
                        resultado.inseridos += 1
                    else:
                        contrato = existente
                        alterou = False
                        for campo, valor in payload.items():
                            if getattr(existente, campo) != valor:
                                setattr(existente, campo, valor)
                                alterou = True
                        if alterou:
                            resultado.atualizados += 1
                        else:
                            resultado.ignorados += 1
                        session.query(ContratoDespesaOrcamentaria).filter(
                            ContratoDespesaOrcamentaria.contrato_id == contrato.id
                        ).delete()
                        session.query(ContratoItemAdquirido).filter(
                            ContratoItemAdquirido.contrato_id == contrato.id
                        ).delete()

                    for ordem, despesa in enumerate(
                        registro.get("despesas_orcamentarias", []),
                        start=1,
                    ):
                        session.add(
                            ContratoDespesaOrcamentaria(
                                contrato_id=contrato.id,
                                ordem=ordem,
                                unidade_gestora=despesa.get("unidade_gestora"),
                                exercicio=despesa.get("exercicio"),
                                orgao=despesa.get("orgao"),
                                unidade=despesa.get("unidade"),
                                departamento=despesa.get("departamento"),
                                fonte_recurso=despesa.get("fonte_recurso"),
                                natureza_despesa_rubrica=despesa.get(
                                    "natureza_despesa_rubrica"
                                ),
                                descricao_despesa=despesa.get("descricao_despesa"),
                                valor_despesa=despesa.get("valor_despesa"),
                            )
                        )

                    for ordem, item in enumerate(
                        registro.get("itens_adquiridos", []),
                        start=1,
                    ):
                        session.add(
                            ContratoItemAdquirido(
                                contrato_id=contrato.id,
                                ordem=ordem,
                                unidade_gestora=item.get("unidade_gestora"),
                                numero_lote=item.get("numero_lote"),
                                numero_item=item.get("numero_item"),
                                identificacao=item.get("identificacao"),
                                quantidade=item.get("quantidade"),
                                valor_unitario=item.get("valor_unitario"),
                                valor_total=item.get("valor_total"),
                            )
                        )
            except Exception:
                session.rollback()
                resultado.erros += 1
        return resultado

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
                                Licitacao.data_abertura
                                == registro_base["data_abertura"],
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

                        session.query(VencedorLicitacao).filter(
                            VencedorLicitacao.licitacao_id == licitacao.id
                        ).delete()
                        session.query(MateriaInstrumento).filter(
                            MateriaInstrumento.instrumento_id.in_(
                                select(InstrumentoContratual.id).where(
                                    InstrumentoContratual.licitacao_id == licitacao.id
                                )
                            )
                        ).delete(synchronize_session=False)
                        session.query(InstrumentoContratual).filter(
                            InstrumentoContratual.licitacao_id == licitacao.id
                        ).delete()

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
                        if instrumento.get("cnpj_fornecedor") and instrumento.get(
                            "nome_fornecedor"
                        ):
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
                            tipo_instrumento_contratual=instrumento.get(
                                "tipo_instrumento_contratual"
                            ),
                            numero_instrumento=instrumento.get("numero_instrumento"),
                            tipo_contrato=instrumento.get("tipo_contrato"),
                            objeto=instrumento.get("objeto"),
                            data_emissao=self._to_date(instrumento.get("data_emissao")),
                            data_expiracao=self._to_date(
                                instrumento.get("data_expiracao")
                            ),
                            possui_aditivo=instrumento.get("possui_aditivo"),
                            valor_instrumento_contratual=instrumento.get(
                                "valor_instrumento_contratual"
                            ),
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

    def _load_receitas(self, session, ano: Optional[int]) -> LoadResult:
        """Carrega arrecadações e lançamentos de receitas."""
        resultado = LoadResult()
        parser = ReceitasParser()

        arquivos_arrec = sorted(self.data_dir.rglob("*arrecadacao*.xml"))
        arquivos_lanc = sorted(self.data_dir.rglob("*lancamento*.xml"))
        if ano is not None:
            mark = str(ano)
            arquivos_arrec = [p for p in arquivos_arrec if mark in p.name]
            arquivos_lanc = [p for p in arquivos_lanc if mark in p.name]

        for arq in arquivos_arrec:
            for reg in parser.parse_arrecadacoes(str(arq)):
                try:
                    with session.begin():
                        natureza = self._get_or_create_natureza(
                            session, reg.get("natureza") or {}
                        )
                        existente = session.execute(
                            select(ReceitaArrecadacao).where(
                                and_(
                                    ReceitaArrecadacao.data_arrecadacao
                                    == self._to_date(reg["data_arrecadacao"]),
                                    ReceitaArrecadacao.unidade_gestora
                                    == reg["unidade_gestora"],
                                    ReceitaArrecadacao.natureza_id
                                    == (natureza.id if natureza else None),
                                    ReceitaArrecadacao.fonte_recurso
                                    == reg.get("fonte_recurso"),
                                )
                            )
                        ).scalar_one_or_none()
                        payload = {
                            "exercicio": reg["exercicio"],
                            "mes": reg["mes"],
                            "data_arrecadacao": self._to_date(reg["data_arrecadacao"]),
                            "unidade_gestora": reg["unidade_gestora"],
                            "natureza_id": natureza.id if natureza else None,
                            "fonte_recurso": reg.get("fonte_recurso"),
                            "valor_previsto_bruto": reg.get("valor_previsto_bruto"),
                            "valor_arrecadado_bruto": reg.get("valor_arrecadado_bruto"),
                            "valor_previsto_deducoes": reg.get(
                                "valor_previsto_deducoes"
                            ),
                            "valor_realizado_deducoes": reg.get(
                                "valor_realizado_deducoes"
                            ),
                            "valor_previsto_liquido": reg.get("valor_previsto_liquido"),
                            "valor_arrecadado_liquido": reg.get(
                                "valor_arrecadado_liquido"
                            ),
                        }
                        if existente is None:
                            session.add(ReceitaArrecadacao(**payload))
                            resultado.inseridos += 1
                        else:
                            alterou = False
                            for k, v in payload.items():
                                if getattr(existente, k) != v:
                                    setattr(existente, k, v)
                                    alterou = True
                            if alterou:
                                resultado.atualizados += 1
                            else:
                                resultado.ignorados += 1
                except Exception:
                    session.rollback()
                    resultado.erros += 1

        loader = SQLLoader(session=session, batch_size=self.batch_size)
        for arq in arquivos_lanc:
            regs = parser.parse_lancamentos(str(arq))
            r = loader.load(regs, ReceitaLancamento)
            resultado.inseridos += r.inseridos
            resultado.atualizados += r.atualizados
            resultado.ignorados += r.ignorados
            resultado.erros += r.erros

        return resultado

    def _load_frotas(self, session, registros: list[dict[str, Any]]) -> LoadResult:
        """Carrega veículos de frota e despesas relacionadas."""
        resultado = LoadResult()
        for registro in registros:
            try:
                with session.begin():
                    placa_veiculo = registro.get("placa_veiculo")
                    veiculo = session.execute(
                        select(FrotaVeiculo).where(
                            and_(
                                FrotaVeiculo.codigo_veiculo
                                == registro["codigo_veiculo"],
                                FrotaVeiculo.placa_veiculo == placa_veiculo,
                            )
                        )
                    ).scalar_one_or_none()

                    payload = dict(registro)
                    payload["data_aquisicao"] = self._to_datetime(
                        payload.get("data_aquisicao")
                    )
                    despesas = payload.pop("despesas", [])

                    if veiculo is None:
                        veiculo = FrotaVeiculo(**payload)
                        session.add(veiculo)
                        session.flush()
                        resultado.inseridos += 1
                    else:
                        alterou = False
                        for campo, valor in payload.items():
                            if getattr(veiculo, campo) != valor:
                                setattr(veiculo, campo, valor)
                                alterou = True
                        if alterou:
                            resultado.atualizados += 1
                        else:
                            resultado.ignorados += 1
                        session.query(FrotaDespesa).filter(
                            FrotaDespesa.veiculo_id == veiculo.id
                        ).delete()

                    for despesa in despesas:
                        session.add(
                            FrotaDespesa(
                                veiculo_id=veiculo.id,
                                descricao_evento=despesa.get("descricao_evento"),
                                quantidade_lancamento=despesa.get(
                                    "quantidade_lancamento"
                                ),
                                valor_lancamento=despesa.get("valor_lancamento"),
                                data_evento=self._to_date(despesa.get("data_evento")),
                                tp_despesa=despesa.get("tp_despesa"),
                                tipo_despesa=despesa.get("tipo_despesa"),
                                total_despesa=despesa.get("total_despesa"),
                            )
                        )
            except Exception:
                session.rollback()
                resultado.erros += 1
        return resultado

    def _load_folha_pagamento(self, session, ano: Optional[int]) -> LoadResult:
        """Carrega folha de pagamento em modelo dimensional."""
        resultado = LoadResult()
        parser = FolhaPagamentoParser()
        arquivos = sorted(self.data_dir.rglob("*folha-pagamento*.xml"))
        if ano is not None:
            mark = str(ano)
            arquivos = [p for p in arquivos if mark in p.name]

        for arq in arquivos:
            registros = parser.parse(str(arq))
            for reg in registros:
                try:
                    with session.begin():
                        servidor = self._get_or_create_folha_servidor(
                            session=session,
                            nome=reg["nome_servidor"],
                            cargo=reg.get("cargo"),
                            lotacao=reg.get("lotacao"),
                        )
                        lotacao = self._get_or_create_folha_dim(
                            session, FolhaLotacao, reg.get("lotacao")
                        )
                        cargo = self._get_or_create_folha_dim(
                            session, FolhaCargo, reg.get("cargo")
                        )
                        existente = session.execute(
                            select(FolhaPagamentoRegistro).where(
                                and_(
                                    FolhaPagamentoRegistro.competencia_ano
                                    == reg["competencia_ano"],
                                    FolhaPagamentoRegistro.competencia_mes_nome
                                    == reg["competencia_mes_nome"],
                                    FolhaPagamentoRegistro.servidor_id == servidor.id,
                                    FolhaPagamentoRegistro.cargo_id
                                    == (cargo.id if cargo else None),
                                    FolhaPagamentoRegistro.lotacao_id
                                    == (lotacao.id if lotacao else None),
                                )
                            )
                        ).scalar_one_or_none()
                        payload = {
                            "competencia_ano": reg["competencia_ano"],
                            "competencia_mes_num": reg["competencia_mes_num"],
                            "competencia_mes_nome": reg["competencia_mes_nome"],
                            "servidor_id": servidor.id,
                            "lotacao_id": lotacao.id if lotacao else None,
                            "cargo_id": cargo.id if cargo else None,
                            "salario_base": reg.get("salario_base"),
                            "proventos": reg.get("proventos"),
                            "vantagens": reg.get("vantagens"),
                            "vencimentos_totais": reg.get("vencimentos_totais"),
                            "descontos": reg.get("descontos"),
                            "liquido": reg.get("liquido"),
                        }
                        if existente is None:
                            session.add(FolhaPagamentoRegistro(**payload))
                            resultado.inseridos += 1
                        else:
                            alterou = False
                            for k, v in payload.items():
                                if getattr(existente, k) != v:
                                    setattr(existente, k, v)
                                    alterou = True
                            if alterou:
                                resultado.atualizados += 1
                            else:
                                resultado.ignorados += 1
                except Exception:
                    session.rollback()
                    resultado.erros += 1
        return resultado

    @staticmethod
    def _get_or_create_fornecedor(session, cnpj_cpf: str, nome: str) -> Fornecedor:
        """Busca fornecedor existente ou cria novo registro."""
        fornecedor = session.execute(
            select(Fornecedor).where(
                and_(Fornecedor.cnpj_cpf == cnpj_cpf, Fornecedor.nome == nome)
            )
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

    @staticmethod
    def _to_datetime(value: Any) -> Any:
        """Converte string ISO para datetime quando necessário."""
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @staticmethod
    def _get_or_create_natureza(
        session, natureza: dict[str, Any]
    ) -> Optional[ReceitaNatureza]:
        """Busca ou cria natureza de receita por identificação."""
        ident = natureza.get("identificacao")
        if not ident:
            return None
        existente = session.execute(
            select(ReceitaNatureza).where(ReceitaNatureza.identificacao == ident)
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        obj = ReceitaNatureza(
            identificacao=ident,
            nome=natureza.get("nome"),
            nivel=natureza.get("nivel"),
            identificacao_superior=natureza.get("identificacao_superior"),
        )
        session.add(obj)
        session.flush()
        return obj

    @staticmethod
    def _get_or_create_folha_dim(session, model, nome: Optional[str]):
        """Busca ou cria dimensão textual da folha."""
        if not nome:
            return None
        existente = session.execute(
            select(model).where(model.nome == nome)
        ).scalar_one_or_none()
        if existente is not None:
            return existente
        obj = model(nome=nome)
        session.add(obj)
        session.flush()
        return obj

    @staticmethod
    def _get_or_create_folha_servidor(
        session,
        nome: str,
        cargo: Optional[str],
        lotacao: Optional[str],
    ) -> FolhaServidor:
        """Busca/cria dimensão de folha e tenta vincular ao servidor canônico."""
        existente = session.execute(
            select(FolhaServidor).where(FolhaServidor.nome == nome)
        ).scalar_one_or_none()
        servidor_canonico = IngestionPipeline._find_servidor_canonico(
            session=session,
            nome=nome,
            cargo=cargo,
            secretaria=lotacao,
        )

        if existente is not None:
            if existente.servidor_id is None and servidor_canonico is not None:
                existente.servidor_id = servidor_canonico.id
            return existente

        obj = FolhaServidor(
            nome=nome,
            servidor_id=servidor_canonico.id if servidor_canonico is not None else None,
        )
        session.add(obj)
        session.flush()
        return obj

    @staticmethod
    def _find_servidor_canonico(
        session,
        nome: str,
        cargo: Optional[str],
        secretaria: Optional[str],
    ) -> Optional[Servidor]:
        """Resolve o melhor servidor canônico para um nome da folha."""
        filtros = [Servidor.nome == nome]
        if cargo:
            filtros.append(Servidor.cargo == cargo)
        if secretaria:
            filtros.append(Servidor.secretaria == secretaria)

        candidatos = (
            session.execute(
                select(Servidor)
                .where(and_(*filtros))
                .order_by(
                    Servidor.competencia_referencia.desc(),
                    Servidor.id.desc(),
                )
            )
            .scalars()
            .all()
        )
        if candidatos:
            return candidatos[0]

        if cargo or secretaria:
            fallback = (
                session.execute(
                    select(Servidor)
                    .where(Servidor.nome == nome)
                    .order_by(
                        Servidor.competencia_referencia.desc(),
                        Servidor.id.desc(),
                    )
                )
                .scalars()
                .all()
            )
            if len(fallback) == 1:
                return fallback[0]

        return None

    def _arquivos_por_tipo(self, tipo: str, ano: Optional[int]) -> list[Path]:
        """Descobre arquivos de entrada por tipo e ano."""
        if tipo == "receitas":
            arquivos = sorted(self.data_dir.rglob("*arrecadacao*.xml")) + sorted(
                self.data_dir.rglob("*lancamento*.xml")
            )
        elif tipo == "folha_pagamento":
            arquivos = sorted(self.data_dir.rglob("*folha-pagamento*.xml"))
        elif tipo == "planejamentos":
            arquivos = sorted(self.data_dir.rglob("*planejamento*.xml"))
        elif tipo == "servidores":
            arquivos = sorted(self.data_dir.rglob("*servidores*.xml"))
            if not arquivos:
                arquivos = sorted(self.data_dir.rglob("*folha-pagamento*.xml"))
        elif tipo == "contratos":
            arquivos = sorted(self.data_dir.rglob("*contrato*.xml"))
            if not arquivos:
                arquivos = sorted(self.data_dir.rglob("*licitacoes*.xml"))
        else:
            arquivos = sorted(self.data_dir.rglob(f"*{tipo}*.xml"))
        if ano is None:
            return arquivos
        marcador = str(ano)
        return [arquivo for arquivo in arquivos if marcador in arquivo.name]
