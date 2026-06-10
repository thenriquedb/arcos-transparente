"""Modelos ORM de contratos e seus detalhes (despesas e itens)."""

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
    from database.models.bidding import Fornecedor


class Contrato(Base):
    __tablename__ = "contratos"
    __table_args__ = (
        UniqueConstraint("numero", "data_inicio", name="uq_contrato_numero_data_inicio"),
        Index(
            "ix_contratos_secretaria_categoria_data_inicio",
            "secretaria",
            "categoria",
            "data_inicio",
        ),
        Index(
            "ix_contratos_numero_licitatorio_data_inicio",
            "numero_licitatorio",
            "data_inicio",
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
    numero_licitatorio: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    numero_instrumento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tipo_instrumento_contratual: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    fornecedor: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    possui_aditivo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    descricao_despesa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    xml_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fornecedor_rel: Mapped[Optional["Fornecedor"]] = relationship(back_populates="contratos")
    despesas_orcamentarias: Mapped[list["ContratoDespesaOrcamentaria"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )
    itens_adquiridos: Mapped[list["ContratoItemAdquirido"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )


class ContratoDespesaOrcamentaria(Base):
    __tablename__ = "contrato_despesas_orcamentarias"
    __table_args__ = (
        UniqueConstraint(
            "contrato_id",
            "ordem",
            name="uq_contrato_despesa_ordem",
        ),
        Index(
            "ix_contrato_despesa_classificacao",
            "descricao_despesa",
            "natureza_despesa_rubrica",
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
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey("contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(nullable=False)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    exercicio: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    orgao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fonte_recurso: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    natureza_despesa_rubrica: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    descricao_despesa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_despesa: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    contrato: Mapped["Contrato"] = relationship(back_populates="despesas_orcamentarias")


class ContratoItemAdquirido(Base):
    __tablename__ = "contrato_itens_adquiridos"
    __table_args__ = (
        UniqueConstraint(
            "contrato_id",
            "ordem",
            name="uq_contrato_item_ordem",
        ),
        Index(
            "ix_contrato_item_lote_item",
            "numero_lote",
            "numero_item",
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
    contrato_id: Mapped[int] = mapped_column(
        ForeignKey("contratos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(nullable=False)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    numero_lote: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    numero_item: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    identificacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valor_unitario: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    contrato: Mapped["Contrato"] = relationship(back_populates="itens_adquiridos")
