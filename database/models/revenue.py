from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class ReceitaNatureza(Base):
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
    __tablename__ = "receita_arrecadacoes"
    __table_args__ = (UniqueConstraint("data_arrecadacao", "unidade_gestora", "natureza_id", "fonte_recurso", name="uq_receita_arrec_base"),)

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
    __tablename__ = "receita_lancamentos"
    __table_args__ = (UniqueConstraint("data_lancamento", "tipo_receita", "tributo", "valor_lancado_exercicio", name="uq_receita_lanc_base"),)

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
