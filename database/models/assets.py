"""Modelo ORM de bens patrimoniais."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class Patrimonio(Base):
    """Bens patrimoniais importados dos XMLs de administracao."""

    __tablename__ = "patrimonios"
    __table_args__ = (
        UniqueConstraint(
            "unidade_gestora",
            "placa",
            name="uq_patrimonio_unidade_placa",
        ),
        Index("ix_patrimonios_localizacao_status", "localizacao", "status"),
        Index("ix_patrimonios_classificacao", "classificacao"),
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

    unidade_gestora: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    placa: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    situacao_bem: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True, index=True
    )
    comandatario: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    classificacao: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    descricao_item: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_ingresso: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True, index=True
    )
    data_aquisicao: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, index=True
    )
    data_baixa: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    localizacao: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    status: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    valor_ingresso: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_atualizado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
