"""Modelos ORM do Observatorio Arcos."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa para os modelos ORM."""


class Contrato(Base):
    """Representa contratos públicos importados do portal."""

    __tablename__ = "contratos"
    __table_args__ = (
        UniqueConstraint("numero", "data_inicio", name="uq_contrato_numero_data_inicio"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    fornecedor: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Licitacao(Base):
    """Representa licitações públicas importadas do portal."""

    __tablename__ = "licitacoes"
    __table_args__ = (
        UniqueConstraint("numero", "data_abertura", name="uq_licitacao_numero_data_abertura"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    modalidade: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    objeto: Mapped[str] = mapped_column(Text, nullable=False)
    valor_estimado: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_abertura: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    situacao: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vencedores: Mapped[list["VencedorLicitacao"]] = relationship(
        back_populates="licitacao",
        cascade="all, delete-orphan",
    )
    instrumentos_contratuais: Mapped[list["InstrumentoContratual"]] = relationship(
        back_populates="licitacao",
        cascade="all, delete-orphan",
    )


class Fornecedor(Base):
    """Cadastro de fornecedores relacionados às licitações."""

    __tablename__ = "fornecedores"
    __table_args__ = (
        UniqueConstraint("cnpj_cpf", "nome", name="uq_fornecedor_cnpj_nome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    cnpj_cpf: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    vencedores: Mapped[list["VencedorLicitacao"]] = relationship(back_populates="fornecedor")
    instrumentos_contratuais: Mapped[list["InstrumentoContratual"]] = relationship(back_populates="fornecedor")


class VencedorLicitacao(Base):
    """Vencedores vinculados a cada licitação."""

    __tablename__ = "vencedores_licitacao"
    __table_args__ = (
        UniqueConstraint("licitacao_id", "cnpj_cpf", "nome", name="uq_vencedor_licitacao_doc_nome"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    licitacao_id: Mapped[int] = mapped_column(ForeignKey("licitacoes.id", ondelete="CASCADE"), nullable=False, index=True)
    fornecedor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True)
    cnpj_cpf: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    validade_proposta: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    licitacao: Mapped["Licitacao"] = relationship(back_populates="vencedores")
    fornecedor: Mapped[Optional["Fornecedor"]] = relationship(back_populates="vencedores")


class InstrumentoContratual(Base):
    """Instrumentos contratuais vinculados à licitação."""

    __tablename__ = "instrumentos_contratuais"
    __table_args__ = (
        UniqueConstraint("licitacao_id", "numero_instrumento", name="uq_instrumento_licitacao_numero"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    licitacao_id: Mapped[int] = mapped_column(ForeignKey("licitacoes.id", ondelete="CASCADE"), nullable=False, index=True)
    fornecedor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True)
    numero_licitatorio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    tipo_instrumento_contratual: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    numero_instrumento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tipo_contrato: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    objeto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_emissao: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    data_expiracao: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    possui_aditivo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    valor_instrumento_contratual: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    licitacao: Mapped["Licitacao"] = relationship(back_populates="instrumentos_contratuais")
    fornecedor: Mapped[Optional["Fornecedor"]] = relationship(back_populates="instrumentos_contratuais")
    materias: Mapped[list["MateriaInstrumento"]] = relationship(back_populates="instrumento", cascade="all, delete-orphan")


class MateriaInstrumento(Base):
    """Materiais/itens adquiridos por instrumento contratual."""

    __tablename__ = "materias_instrumento"
    __table_args__ = (
        UniqueConstraint("instrumento_id", "numero_lote", "numero_item", name="uq_materia_instrumento_lote_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    instrumento_id: Mapped[int] = mapped_column(
        ForeignKey("instrumentos_contratuais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    numero_lote: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    numero_item: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    identificacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valor_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    instrumento: Mapped["InstrumentoContratual"] = relationship(back_populates="materias")


class Servidor(Base):
    """Representa registros de servidores públicos."""

    __tablename__ = "servidores"
    __table_args__ = (
        UniqueConstraint("nome", "cargo", "secretaria", "data_admissao", name="uq_servidor_nome_cargo_sec_data_admissao"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    salario_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    data_admissao: Mapped[date] = mapped_column(Date, nullable=False, index=True)


class FrotaVeiculo(Base):
    """Veículos de frota importados do XML de administração de frotas."""

    __tablename__ = "frota_veiculos"
    __table_args__ = (
        UniqueConstraint("codigo_veiculo", "placa_veiculo", name="uq_frota_codigo_placa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    codigo_veiculo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    placa_patrimonio: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    placa_veiculo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    descricao_material: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tipo_veiculo: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    marca: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    modelo: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    data_aquisicao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, index=True)
    localizacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ano_fabricacao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    situacao_veiculo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, index=True)
    situacao_veiculo_patrimonio: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    estado_conservacao: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    renavam: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    chassi: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    ano_modelo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qtd_passageiros: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    marcador_atual: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    unidade_medida: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fornecedor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    cor_predominante: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    valor_atual: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    despesas: Mapped[list["FrotaDespesa"]] = relationship(
        back_populates="veiculo",
        cascade="all, delete-orphan",
    )


class FrotaDespesa(Base):
    """Despesas detalhadas por veículo de frota."""

    __tablename__ = "frota_despesas"
    __table_args__ = (
        UniqueConstraint("veiculo_id", "descricao_evento", "data_evento", "valor_lancamento", name="uq_frota_despesa_evento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    veiculo_id: Mapped[int] = mapped_column(ForeignKey("frota_veiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao_evento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade_lancamento: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valor_lancamento: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    data_evento: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    tp_despesa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo_despesa: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    total_despesa: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)

    veiculo: Mapped["FrotaVeiculo"] = relationship(back_populates="despesas")


class ReceitaNatureza(Base):
    """Natureza/categoria de receita para arrecadações."""

    __tablename__ = "receita_naturezas"
    __table_args__ = (UniqueConstraint("identificacao", name="uq_receita_natureza_identificacao"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    identificacao: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    nivel: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    identificacao_superior: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)

    arrecadacoes: Mapped[list["ReceitaArrecadacao"]] = relationship(back_populates="natureza")


class ReceitaArrecadacao(Base):
    """Arrecadações de receitas com valores previstos e realizados."""

    __tablename__ = "receita_arrecadacoes"
    __table_args__ = (
        UniqueConstraint("data_arrecadacao", "unidade_gestora", "natureza_id", "fonte_recurso", name="uq_receita_arrec_base"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    data_arrecadacao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    unidade_gestora: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    natureza_id: Mapped[Optional[int]] = mapped_column(ForeignKey("receita_naturezas.id", ondelete="SET NULL"), nullable=True, index=True)
    fonte_recurso: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_previsto_bruto: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_arrecadado_bruto: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_previsto_deducoes: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_realizado_deducoes: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_previsto_liquido: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_arrecadado_liquido: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    natureza: Mapped[Optional["ReceitaNatureza"]] = relationship(back_populates="arrecadacoes")


class ReceitaLancamento(Base):
    """Lançamentos de receitas tributárias."""

    __tablename__ = "receita_lancamentos"
    __table_args__ = (
        UniqueConstraint("data_lancamento", "tipo_receita", "tributo", "valor_lancado_exercicio", name="uq_receita_lanc_base"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    data_lancamento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_receita: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    tributo: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    valor_lancado_exercicio: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_lancado_divida_ativa: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_lancado_cobraca_judicial: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)


class FolhaServidor(Base):
    """Dimensão de servidor para folha de pagamento."""

    __tablename__ = "folha_servidores"
    __table_args__ = (UniqueConstraint("nome", name="uq_folha_servidor_nome"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(back_populates="servidor")


class FolhaLotacao(Base):
    """Dimensão de lotação da folha."""

    __tablename__ = "folha_lotacoes"
    __table_args__ = (UniqueConstraint("nome", name="uq_folha_lotacao_nome"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(back_populates="lotacao")


class FolhaCargo(Base):
    """Dimensão de cargo da folha."""

    __tablename__ = "folha_cargos"
    __table_args__ = (UniqueConstraint("nome", name="uq_folha_cargo_nome"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(back_populates="cargo")


class FolhaPagamentoRegistro(Base):
    """Fato mensal de folha por servidor/cargo/lotação."""

    __tablename__ = "folha_pagamentos"
    __table_args__ = (
        UniqueConstraint(
            "competencia_ano",
            "competencia_mes_nome",
            "servidor_id",
            "cargo_id",
            "lotacao_id",
            name="uq_folha_comp_servidor_cargo_lotacao",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    competencia_ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    competencia_mes_num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    competencia_mes_nome: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    servidor_id: Mapped[int] = mapped_column(ForeignKey("folha_servidores.id", ondelete="CASCADE"), nullable=False, index=True)
    lotacao_id: Mapped[int] = mapped_column(ForeignKey("folha_lotacoes.id", ondelete="SET NULL"), nullable=True, index=True)
    cargo_id: Mapped[int] = mapped_column(ForeignKey("folha_cargos.id", ondelete="SET NULL"), nullable=True, index=True)
    salario_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    proventos: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    vantagens: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    vencimentos_totais: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    descontos: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    liquido: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    servidor: Mapped["FolhaServidor"] = relationship(back_populates="pagamentos")
    lotacao: Mapped[Optional["FolhaLotacao"]] = relationship(back_populates="pagamentos")
    cargo: Mapped[Optional["FolhaCargo"]] = relationship(back_populates="pagamentos")
