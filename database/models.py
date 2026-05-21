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
        UniqueConstraint("nome", "cargo", "data_admissao", name="uq_servidor_nome_cargo_data_admissao"),
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
    salario_base: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_admissao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
