"""Modelo ORM de servidores municipais."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class Servidor(Base):
    """Representa o cadastro funcional importado do JSON de servidores."""

    __tablename__ = "servidores"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_servidores_source_id"),
        Index("ix_servidores_nome", "nome"),
        Index("ix_servidores_matricula", "matricula"),
        Index("ix_servidores_lotacao", "lotacao"),
        Index("ix_servidores_competencia_referencia", "competencia_referencia"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    competencia_referencia: Mapped[date] = mapped_column(Date, nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    matricula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cargo_funcao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fundamento_legal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    lotacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    situacao_funcional: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    forma_contratacao_investidura: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    data_admissao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_desligamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    horario_trabalho: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    carga_horaria: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    local_origem_cedencia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    local_destino_cedencia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    onus_pagamento_cedencia: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    data_inicio_cessao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_fim_cessao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    regime_aposentadoria: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    vinculo_empregaticio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class QuadroPessoal(Base):
    """Totais mensais de vagas por regime de contratacao."""

    __tablename__ = "quadro_pessoal"
    __table_args__ = (
        UniqueConstraint(
            "origem",
            "competencia_referencia",
            "regime_contratacao",
            name="uq_quadro_pessoal_origem_comp_regime",
        ),
        Index(
            "ix_quadro_pessoal_origem_competencia",
            "origem",
            "competencia_referencia",
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
    competencia_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    regime_contratacao: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    vagas_criadas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vagas_preenchidas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
