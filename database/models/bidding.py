"""Modelo ORM de licitacoes."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from database.models.contracts import Contrato


class Licitacao(Base):
    __tablename__ = "licitacoes"
    __table_args__ = (
        UniqueConstraint("numero", "data_abertura", name="uq_licitacao_numero_data_abertura"),
        Index(
            "ix_licitacoes_secretaria_situacao_data_abertura",
            "secretaria",
            "situacao",
            "data_abertura",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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
        back_populates="licitacao", cascade="all, delete-orphan"
    )
    instrumentos_contratuais: Mapped[list["InstrumentoContratual"]] = relationship(
        back_populates="licitacao", cascade="all, delete-orphan"
    )


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    __table_args__ = (UniqueConstraint("cnpj_cpf", "nome", name="uq_fornecedor_cnpj_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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
    contratos: Mapped[list["Contrato"]] = relationship(back_populates="fornecedor_rel")


class VencedorLicitacao(Base):
    __tablename__ = "vencedores_licitacao"
    __table_args__ = (UniqueConstraint("licitacao_id", "cnpj_cpf", "nome", name="uq_vencedor_licitacao_doc_nome"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    licitacao_id: Mapped[int] = mapped_column(
        ForeignKey("licitacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
    )
    cnpj_cpf: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    validade_proposta: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    licitacao: Mapped["Licitacao"] = relationship(back_populates="vencedores")
    fornecedor: Mapped[Optional["Fornecedor"]] = relationship(back_populates="vencedores")


class InstrumentoContratual(Base):
    __tablename__ = "instrumentos_contratuais"
    __table_args__ = (
        UniqueConstraint("licitacao_id", "numero_instrumento", name="uq_instrumento_licitacao_numero"),
        Index(
            "ix_instrumentos_contratuais_fornecedor_emissao",
            "fornecedor_id",
            "data_emissao",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    licitacao_id: Mapped[int] = mapped_column(
        ForeignKey("licitacoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
    materias: Mapped[list["MateriaInstrumento"]] = relationship(
        back_populates="instrumento", cascade="all, delete-orphan"
    )


class MateriaInstrumento(Base):
    __tablename__ = "materias_instrumento"
    __table_args__ = (
        UniqueConstraint(
            "instrumento_id",
            "numero_lote",
            "numero_item",
            name="uq_materia_instrumento_lote_item",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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
