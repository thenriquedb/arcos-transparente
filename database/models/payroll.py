"""Modelos ORM de folha de pagamento (servidor, registros, snapshot)."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class FolhaServidor(Base):
    __tablename__ = "folha_servidores"
    __table_args__ = (
        UniqueConstraint(
            "nome",
            "cargo",
            "secretaria",
            "competencia_referencia",
            name="uq_folha_servidor_nome_cargo_sec_comp_ref",
        ),
        Index("ix_folha_servidores_nome", "nome"),
        Index(
            "ix_folha_servidores_secretaria_cargo_comp_ref",
            "secretaria",
            "cargo",
            "competencia_referencia",
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
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    salario_base: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    competencia_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(
        back_populates="servidor"
    )


class FolhaLotacao(Base):
    __tablename__ = "folha_lotacoes"
    __table_args__ = (UniqueConstraint("nome", name="uq_folha_lotacao_nome"),)

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
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(
        back_populates="lotacao"
    )


class FolhaCargo(Base):
    __tablename__ = "folha_cargos"
    __table_args__ = (UniqueConstraint("nome", name="uq_folha_cargo_nome"),)

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
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    pagamentos: Mapped[list["FolhaPagamentoRegistro"]] = relationship(
        back_populates="cargo"
    )


class FolhaPagamentoRegistro(Base):
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
        Index(
            "ix_folha_pagamentos_ano_mes_lotacao",
            "competencia_ano",
            "competencia_mes_num",
            "lotacao_id",
        ),
        Index(
            "ix_folha_pagamentos_ano_mes_servidor",
            "competencia_ano",
            "competencia_mes_num",
            "servidor_id",
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
    competencia_ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    competencia_mes_num: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    competencia_mes_nome: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    servidor_id: Mapped[int] = mapped_column(
        ForeignKey("folha_servidores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lotacao_id: Mapped[int] = mapped_column(
        ForeignKey("folha_lotacoes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cargo_id: Mapped[int] = mapped_column(
        ForeignKey("folha_cargos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    salario_base: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    proventos: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    vantagens: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    vencimentos_totais: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    descontos: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    liquido: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    servidor: Mapped["FolhaServidor"] = relationship(back_populates="pagamentos")
    lotacao: Mapped[Optional["FolhaLotacao"]] = relationship(
        back_populates="pagamentos"
    )
    cargo: Mapped[Optional["FolhaCargo"]] = relationship(back_populates="pagamentos")
