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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base


class DespesaDocumento(Base):
    """Documento de despesa: empenho, resto a pagar ou documento extra."""

    __tablename__ = "despesa_documentos"
    __table_args__ = (
        UniqueConstraint(
            "tipo_origem",
            "arquivo_origem",
            "sequencia_origem",
            name="uq_despesa_documento_base",
        ),
        Index("ix_despesa_documentos_tipo_exercicio", "tipo_origem", "exercicio"),
        Index("ix_despesa_documentos_data", "data_documento"),
        Index("ix_despesa_documentos_credor", "credor"),
        Index("ix_despesa_documentos_funcao", "funcao"),
        Index("ix_despesa_documentos_numero_contrato", "numero_contrato"),
        Index("ix_despesa_documentos_conta_extra", "conta_extra_identificacao"),
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

    tipo_origem: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    arquivo_origem: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sequencia_origem: Mapped[int] = mapped_column(Integer, nullable=False)
    origem: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    exercicio: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    unidade_gestora: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    orgao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    departamento: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    funcao: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    subfuncao: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    programa: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tipo_acao: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    descricao_acao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fonte_recurso_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    fonte_recurso_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    esfera_administrativa: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    modalidade_aplicacao_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    modalidade_aplicacao_descricao: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    categoria_economica_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    categoria_economica_descricao: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    grupo_despesa_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    grupo_despesa_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    elemento_despesa_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    elemento_despesa_descricao: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    desdobramento_despesa_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    desdobramento_despesa_descricao: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    conta_extra_identificacao: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    conta_extra_descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    numero_documento: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    data_documento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    periodo_referencia_inicio: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    periodo_referencia_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    categoria_documento: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    credor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cpf_cnpj: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    modalidade_licitacao: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    numero_licitacao: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    ano_licitacao: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data_homologacao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    processo_compra: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    numero_contrato: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    numero_convenio: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    valor_documento: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_empenhado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_liquidacao: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_liquidado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_pago: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    valor_anulado: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    objetivo_viagem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legislacao_associada: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ato_legal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    destino: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data_inicial_viagem: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_final_viagem: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantidade_dias_diarias: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 4), nullable=True
    )
    valor_diaria: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    itens: Mapped[list["DespesaDocumentoItem"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )
    documentos_comprobatorios: Mapped[list["DespesaDocumentoComprobatorio"]] = (
        relationship(back_populates="documento", cascade="all, delete-orphan")
    )


class DespesaDocumentoItem(Base):
    """Item declarado dentro de um documento de despesa."""

    __tablename__ = "despesa_documento_itens"
    __table_args__ = (
        UniqueConstraint(
            "documento_id",
            "ordem",
            name="uq_despesa_documento_item_ordem",
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
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("despesa_documentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    numero_item: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    descricao_item: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantidade: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    valor_unitario: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    valor_total: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    documento: Mapped["DespesaDocumento"] = relationship(back_populates="itens")


class DespesaDocumentoComprobatorio(Base):
    """Documento comprobatorio vinculado a um empenho ou resto a pagar."""

    __tablename__ = "despesa_documentos_comprobatorios"
    __table_args__ = (
        UniqueConstraint(
            "documento_id",
            "ordem",
            name="uq_despesa_documento_comprobatorio_ordem",
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
    documento_id: Mapped[int] = mapped_column(
        ForeignKey("despesa_documentos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    data_liquidacao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    codigo_tipo_documento: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    descricao_tipo_documento: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )
    numero_documento: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    serie_modelo_nota_fiscal: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    descricao_serie: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    chave_acesso: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_emissao_documento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valor_documento: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    numero_empenho: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    codigo_unidade_gestora: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    numero_sequencia: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    documento: Mapped["DespesaDocumento"] = relationship(
        back_populates="documentos_comprobatorios"
    )
