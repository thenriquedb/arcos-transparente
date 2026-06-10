"""Modelos ORM de estoques e movimentacoes de almoxarifado."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class EstoqueMaterial(Base):
    """Saldo sumarizado de um material importado do XML de estoques."""

    __tablename__ = "estoque_materiais"
    __table_args__ = (
        UniqueConstraint(
            "origem",
            "arquivo_origem",
            "sequencia_material",
            name="uq_estoque_material_linhagem",
        ),
        Index("ix_estoque_materiais_exercicio_material", "exercicio", "material"),
        Index("ix_estoque_materiais_origem_periodo", "origem", "periodo_fim"),
        Index("ix_estoque_materiais_unidade_medida", "unidade_medida"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    arquivo_origem: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sequencia_material: Mapped[int] = mapped_column(Integer, nullable=False)
    origem: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material: Mapped[str] = mapped_column(Text, nullable=False)
    unidade_medida: Mapped[str] = mapped_column(String(80), nullable=False)
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fim: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    saldo_anterior_quantidade: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    saldo_anterior_valor: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    entrada_quantidade: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    entrada_valor: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    saida_quantidade: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    saida_valor: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    saldo_quantidade: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    saldo_valor: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )

    movimentacoes: Mapped[list["EstoqueMovimentacao"]] = relationship(
        back_populates="estoque_material",
        cascade="all, delete-orphan",
    )


class EstoqueMovimentacao(Base):
    """Movimentacao diaria de um material de estoque."""

    __tablename__ = "estoque_movimentacoes"
    __table_args__ = (
        UniqueConstraint(
            "material_id",
            "sequencia_movimentacao",
            name="uq_estoque_movimentacao_linhagem",
        ),
        Index("ix_estoque_movimentacoes_data_tipo", "data_movimento", "tipo_movimento"),
        Index("ix_estoque_movimentacoes_almoxarifado", "almoxarifado"),
        Index("ix_estoque_movimentacoes_unidade_gestora", "unidade_gestora"),
        Index("ix_estoque_movimentacoes_classificacao", "classificacao"),
        Index("ix_estoque_movimentacoes_localizacao", "localizacao"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    material_id: Mapped[int] = mapped_column(
        ForeignKey("estoque_materiais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequencia_movimentacao: Mapped[int] = mapped_column(Integer, nullable=False)
    data_movimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_movimento: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    almoxarifado: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    localizacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    classificacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    quantidade: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    valor_unitario: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 8), nullable=True
    )
    valor_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    custo_medio: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 8), nullable=True
    )

    estoque_material: Mapped["EstoqueMaterial"] = relationship(
        back_populates="movimentacoes"
    )
