from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class TransferenciaFinanceiraMovimento(Base):
    """Movimentos financeiros entre unidades públicas."""

    __tablename__ = "transferencias_financeiras_movimentos"
    __table_args__ = (
        UniqueConstraint(
            "arquivo_origem",
            "sequencia_origem",
            name="uq_transf_fin_mov_arquivo_seq",
        ),
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
    sequencia_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, index=True
    )
    unidade_gestora_concessora: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    unidade_gestora_recebedora: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    finalidade: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fonte_recurso: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detalhamento_fonte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    programacao_inicial: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    data_movimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo_movimento: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, index=True
    )
    valor_movimento: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )


class EmendaParlamentar(Base):
    """Emendas parlamentares exportadas em CSV."""

    __tablename__ = "emendas_parlamentares"
    __table_args__ = (
        UniqueConstraint(
            "arquivo_origem",
            "sequencia_origem",
            name="uq_emenda_parl_arquivo_seq",
        ),
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
    sequencia_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    exercicio_consulta: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ano_numero: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    autor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    objeto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo_emenda: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    funcao: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, index=True
    )
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
