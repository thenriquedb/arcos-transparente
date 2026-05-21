from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class FrotaVeiculo(Base):
    """Veiculos de frota importados do XML de administracao de frotas."""

    __tablename__ = "frota_veiculos"
    __table_args__ = (UniqueConstraint("codigo_veiculo", "placa_veiculo", name="uq_frota_codigo_placa"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    codigo_veiculo: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    placa_patrimonio: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    placa_veiculo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    descricao_material: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    unidade_gestora: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tipo_veiculo: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    marca: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    modelo: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    data_aquisicao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True, index=True)
    localizacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ano_fabricacao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    situacao_veiculo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, index=True)
    situacao_veiculo_patrimonio: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    estado_conservacao: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    renavam: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    chassi: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    ano_modelo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qtd_passageiros: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    marcador_atual: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    unidade_medida: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fornecedor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    cor_predominante: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    valor_atual: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    despesas: Mapped[list["FrotaDespesa"]] = relationship(back_populates="veiculo", cascade="all, delete-orphan")


class FrotaDespesa(Base):
    """Despesas detalhadas por veiculo de frota."""

    __tablename__ = "frota_despesas"
    __table_args__ = (UniqueConstraint("veiculo_id", "descricao_evento", "data_evento", "valor_lancamento", name="uq_frota_despesa_evento"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    veiculo_id: Mapped[int] = mapped_column(ForeignKey("frota_veiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    descricao_evento: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade_lancamento: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valor_lancamento: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    data_evento: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    tp_despesa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tipo_despesa: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    total_despesa: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)

    veiculo: Mapped["FrotaVeiculo"] = relationship(back_populates="despesas")
