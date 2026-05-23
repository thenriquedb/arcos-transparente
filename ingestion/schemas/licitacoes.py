"""Schemas Pydantic para ingestao de licitacoes."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class _LicitacoesBaseSchema(BaseModel):
    """Base compartilhada de saneamento para schemas de licitacoes."""

    model_config = ConfigDict(extra="ignore")

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        if isinstance(value, (int, float, Decimal)):
            value = str(value).strip()
            return value or None
        raise ValueError("valor textual invalido")

    @classmethod
    def _parse_decimal(cls, value: Any) -> Decimal | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int):
            return Decimal(value)
        if isinstance(value, float):
            return Decimal(str(value))

        text = cls._clean_text(value)
        if text is None:
            return None

        normalized = text.replace("R$", "").replace(" ", "")
        normalized = normalized.replace(".", "").replace(",", ".")
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("valor decimal invalido") from exc

    @classmethod
    def _parse_date(cls, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = cls._clean_text(value)
        if text is None:
            return None

        if "/" in text:
            try:
                dd, mm, yyyy = text.split("/")
                return date(int(yyyy), int(mm), int(dd))
            except ValueError as exc:
                raise ValueError("data invalida no formato dd/mm/yyyy") from exc

        try:
            return date.fromisoformat(text)
        except ValueError:
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
            except ValueError as exc:
                raise ValueError("data invalida") from exc


class MateriaInstrumentoInSchema(_LicitacoesBaseSchema):
    """Schema de itens adquiridos de um instrumento contratual."""

    unidade_gestora: str | None = None
    numero_lote: str | None = None
    numero_item: str | None = None
    identificacao: str | None = None
    quantidade: Decimal | None = None
    valor_unitario: Decimal | None = None
    valor_total: Decimal | None = None

    @field_validator(
        "unidade_gestora",
        "numero_lote",
        "numero_item",
        "identificacao",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("quantidade", "valor_unitario", "valor_total", mode="before")
    @classmethod
    def _normalize_decimal_fields(cls, value: Any) -> Decimal | None:
        return cls._parse_decimal(value)


class VencedorInSchema(_LicitacoesBaseSchema):
    """Schema de vencedores de uma licitacao."""

    cnpj_cpf: str
    nome: str
    validade_proposta: str | None = None

    @field_validator("cnpj_cpf", "nome", "validade_proposta", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return cls._clean_text(value)


class InstrumentoContratualInSchema(_LicitacoesBaseSchema):
    """Schema de instrumento contratual ligado a uma licitacao."""

    numero_licitatorio: str | None = None
    unidade_gestora: str | None = None
    tipo_instrumento_contratual: str | None = None
    numero_instrumento: str | None = None
    tipo_contrato: str | None = None
    objeto: str | None = None
    data_emissao: date | None = None
    data_expiracao: date | None = None
    cnpj_fornecedor: str | None = None
    nome_fornecedor: str | None = None
    possui_aditivo: str | None = None
    valor_instrumento_contratual: Decimal | None = None
    materias: list[MateriaInstrumentoInSchema] = Field(default_factory=list)

    @field_validator(
        "numero_licitatorio",
        "unidade_gestora",
        "tipo_instrumento_contratual",
        "numero_instrumento",
        "tipo_contrato",
        "objeto",
        "cnpj_fornecedor",
        "nome_fornecedor",
        "possui_aditivo",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("data_emissao", "data_expiracao", mode="before")
    @classmethod
    def _normalize_date_fields(cls, value: Any) -> date | None:
        return cls._parse_date(value)

    @field_validator("valor_instrumento_contratual", mode="before")
    @classmethod
    def _normalize_decimal_fields(cls, value: Any) -> Decimal | None:
        return cls._parse_decimal(value)

    @field_validator("materias", mode="before")
    @classmethod
    def _normalize_materias(
        cls, value: Any
    ) -> list[MateriaInstrumentoInSchema]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("materias deve ser uma lista")

        materias_validas: list[MateriaInstrumentoInSchema] = []
        for item in value:
            try:
                materias_validas.append(MateriaInstrumentoInSchema.model_validate(item))
            except ValidationError:
                continue
        return materias_validas


class LicitacaoInSchema(_LicitacoesBaseSchema):
    """Schema principal de ingestao de licitacoes."""

    numero: str
    modalidade: str
    objeto: str
    valor_estimado: Decimal
    data_abertura: date
    situacao: str | None = "nao_informado"
    secretaria: str | None = "nao_informado"
    vencedores: list[VencedorInSchema] = Field(default_factory=list)
    instrumentos_contratuais: list[InstrumentoContratualInSchema] = Field(
        default_factory=list
    )

    @field_validator("numero", "modalidade", "objeto", "situacao", "secretaria", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return cls._clean_text(value)

    @field_validator("valor_estimado", mode="before")
    @classmethod
    def _normalize_valor_estimado(cls, value: Any) -> Decimal | None:
        return cls._parse_decimal(value)

    @field_validator("data_abertura", mode="before")
    @classmethod
    def _normalize_data_abertura(cls, value: Any) -> date | None:
        return cls._parse_date(value)

    @field_validator("vencedores", mode="before")
    @classmethod
    def _normalize_vencedores(cls, value: Any) -> list[VencedorInSchema]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("vencedores deve ser uma lista")

        vencedores_validos: list[VencedorInSchema] = []
        for item in value:
            try:
                vencedores_validos.append(VencedorInSchema.model_validate(item))
            except ValidationError:
                continue
        return vencedores_validos

    @field_validator("instrumentos_contratuais", mode="before")
    @classmethod
    def _normalize_instrumentos(
        cls, value: Any
    ) -> list[InstrumentoContratualInSchema]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("instrumentos_contratuais deve ser uma lista")

        instrumentos_validos: list[InstrumentoContratualInSchema] = []
        for item in value:
            try:
                instrumentos_validos.append(
                    InstrumentoContratualInSchema.model_validate(item)
                )
            except ValidationError:
                continue
        return instrumentos_validos

    @model_validator(mode="after")
    def _apply_defaults(self) -> LicitacaoInSchema:
        if not self.situacao:
            self.situacao = "nao_informado"
        if not self.secretaria:
            self.secretaria = "nao_informado"
        return self
