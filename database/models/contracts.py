from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from database.models.bidding import Fornecedor


class Contrato(Base):
    __tablename__ = "contratos"
    __table_args__ = (
        UniqueConstraint(
            "numero", "data_inicio", name="uq_contrato_numero_data_inicio"
        ),
        Index(
            "ix_contratos_secretaria_categoria_data_inicio",
            "secretaria",
            "categoria",
            "data_inicio",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    numero: Mapped[str] = mapped_column(String(50), nullable=False)
    fornecedor: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    fornecedor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fornecedores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    secretaria: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    descricao_despesa: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fornecedor_rel: Mapped[Optional["Fornecedor"]] = relationship(
        back_populates="contratos"
    )
