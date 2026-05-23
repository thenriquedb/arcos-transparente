from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class Servidor(Base):
    """Representa registros de servidores publicos."""

    __tablename__ = "servidores"
    __table_args__ = (
        UniqueConstraint(
            "nome",
            "cargo",
            "secretaria",
            "data_admissao",
            name="uq_servidor_nome_cargo_sec_data_admissao",
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
    data_admissao: Mapped[date] = mapped_column(Date, nullable=False, index=True)
