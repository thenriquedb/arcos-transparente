"""Modelo ORM de planejamento orcamentario de despesas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
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


class PlanejamentoDespesa(Base):
    """Registros mensais de planejamento e execucao orcamentaria da despesa."""

    __tablename__ = "planejamento_despesas"
    __table_args__ = (
        UniqueConstraint(
            "origem",
            "exercicio",
            "mes_num",
            "unidade_gestora",
            "orgao",
            "unidade",
            "funcao",
            "subfuncao",
            "programa",
            "tipo_acao",
            "descricao_acao",
            "fonte_recurso_identificacao",
            "categoria_economica_identificacao",
            "grupo_despesa_identificacao",
            "elemento_despesa_identificacao",
            name="uq_planejamento_despesa_base",
        ),
        Index(
            "ix_planejamento_exercicio_mes_funcao",
            "exercicio",
            "mes_num",
            "funcao",
        ),
        Index(
            "ix_planejamento_programa_acao",
            "programa",
            "descricao_acao",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    origem: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mes: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    mes_num: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    unidade_gestora: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    orgao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    funcao: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    subfuncao: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    programa: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tipo_acao: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    descricao_acao: Mapped[str] = mapped_column(Text, nullable=False)
    fonte_recurso_identificacao: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    fonte_recurso_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    esfera_administrativa: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    categoria_economica_identificacao: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    categoria_economica_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grupo_despesa_identificacao: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    grupo_despesa_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    elemento_despesa_identificacao: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    elemento_despesa_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    modalidade_aplicacao_identificacao: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    modalidade_aplicacao_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    dotacao_inicial: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    creditos_adicionais: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    dotacao_atualizada: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_empenhado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_liquidacao: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_liquidado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_pago: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_anulado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
