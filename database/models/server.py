from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base

if TYPE_CHECKING:
    from database.models.payroll import FolhaServidor


class Servidor(Base):
    """Representa snapshots mensais de servidores a partir da folha."""

    __tablename__ = "servidores"
    __table_args__ = (
        UniqueConstraint(
            "nome",
            "cargo",
            "secretaria",
            "competencia_referencia",
            name="uq_servidor_nome_cargo_sec_comp_ref",
        ),
        Index(
            "ix_servidores_secretaria_cargo_comp_ref",
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
    cargo: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    salario_base: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    competencia_referencia: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )

    registros_folha: Mapped[list["FolhaServidor"]] = relationship(
        back_populates="servidor_canonico"
    )


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
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    origem: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    competencia_referencia: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )
    regime_contratacao: Mapped[str] = mapped_column(
        String(120), nullable=False, index=True
    )
    vagas_criadas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vagas_preenchidas: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
