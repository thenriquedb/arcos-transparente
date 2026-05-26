"""Schemas Pydantic para ingestao do quadro de pessoal."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.validation import clean_text, parse_competencia_as_date


class QuadroPessoalInSchema(BaseModel):
    """Schema principal de vagas por regime de contratacao."""

    model_config = ConfigDict(extra="ignore")

    origem: str
    competencia_referencia: date
    regime_contratacao: str
    vagas_criadas: int | None = None
    vagas_preenchidas: int | None = None

    @field_validator("origem", "regime_contratacao", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("competencia_referencia", mode="before")
    @classmethod
    def _normalize_competencia(cls, value: Any) -> date | None:
        return parse_competencia_as_date(value)

    @field_validator("vagas_criadas", "vagas_preenchidas", mode="before")
    @classmethod
    def _normalize_int_fields(cls, value: Any) -> int | None:
        text = clean_text(value)
        if text is None:
            return None
        return int(text)
