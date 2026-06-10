"""Modelo ORM de politicos eleitos."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class Eleito(Base):
    """Representa politicos eleitos e seus mandatos."""

    __tablename__ = "eleitos"
    __table_args__ = (
        UniqueConstraint(
            "tipo_politico",
            "nome_completo",
            "mandato_inicio",
            "mandato_fim",
            name="uq_eleito_tipo_nome_mandato",
        ),
        Index(
            "ix_eleitos_tipo_status_mandato",
            "tipo_politico",
            "mandato_status",
            "mandato_inicio",
            "mandato_fim",
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

    tipo_politico: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    id_origem: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    municipio: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    nome_completo: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_popular: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    partido: Mapped[Optional[str]] = mapped_column(
        String(60), nullable=True, index=True
    )
    telefone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    homepage: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    numero_gabinete: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    biografia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    mandato_inicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mandato_fim: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mandato_status: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    mandato_observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
