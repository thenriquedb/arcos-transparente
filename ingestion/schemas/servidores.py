"""Schemas Pydantic para ingestao de servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from shared.utils.validation import (
    clean_text,
    parse_competencia_as_date,
    parse_date,
    parse_int,
)


class _ServidoresBaseSchema(BaseModel):
    """Base compartilhada de saneamento para schemas de servidores."""

    model_config = ConfigDict(extra="ignore")


class ServidorInSchema(_ServidoresBaseSchema):
    """Schema principal de ingestao do JSON de servidores."""

    source_id: int
    competencia_referencia: date
    nome: str
    cpf: str | None = None
    matricula: str | None = None
    cargo_funcao: str | None = None
    fundamento_legal: str | None = None
    lotacao: str | None = None
    situacao_funcional: str | None = None
    forma_contratacao_investidura: str | None = None
    data_admissao: date | None = None
    data_desligamento: date | None = None
    horario_trabalho: str | None = None
    carga_horaria: str | None = None
    local_origem_cedencia: str | None = None
    local_destino_cedencia: str | None = None
    onus_pagamento_cedencia: str | None = None
    data_inicio_cessao: date | None = None
    data_fim_cessao: date | None = None
    regime_aposentadoria: str | None = None
    vinculo_empregaticio: str | None = None

    @field_validator("source_id", mode="before")
    @classmethod
    def _normalize_source_id(cls, value: Any) -> int | None:
        return parse_int(value)

    @field_validator(
        "nome",
        "cpf",
        "matricula",
        "cargo_funcao",
        "fundamento_legal",
        "lotacao",
        "situacao_funcional",
        "forma_contratacao_investidura",
        "horario_trabalho",
        "carga_horaria",
        "local_origem_cedencia",
        "local_destino_cedencia",
        "onus_pagamento_cedencia",
        "regime_aposentadoria",
        "vinculo_empregaticio",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _normalize_competencia_referencia(cls, value: Any) -> date | None:
        return parse_competencia_as_date(value)

    @field_validator(
        "data_admissao",
        "data_desligamento",
        "data_inicio_cessao",
        "data_fim_cessao",
        mode="before",
    )
    @classmethod
    def _normalize_date_fields(cls, value: Any) -> date | None:
        return parse_date(value)

    @model_validator(mode="after")
    def _apply_defaults(self) -> ServidorInSchema:
        if self.source_id <= 0:
            raise ValueError("source_id deve ser maior que zero")
        return self
