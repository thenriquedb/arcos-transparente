"""Schemas Pydantic para ingestao de politicos eleitos."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from shared.utils.validation import clean_text


class EleitoInSchema(BaseModel):
    """Schema principal de eleitos com mandato individual."""

    model_config = ConfigDict(extra="ignore")

    tipo_politico: str
    id_origem: int | None = None
    municipio: str
    estado: str
    nome_completo: str
    nome_popular: str | None = None
    partido: str | None = None
    telefone: str | None = None
    email: str | None = None
    homepage: str | None = None
    numero_gabinete: str | None = None
    cargo: str | None = None
    biografia: str | None = None
    mandato_inicio: int
    mandato_fim: int
    mandato_status: str
    mandato_observacao: str | None = None

    @field_validator(
        "tipo_politico",
        "municipio",
        "estado",
        "nome_completo",
        "nome_popular",
        "partido",
        "telefone",
        "email",
        "homepage",
        "numero_gabinete",
        "cargo",
        "biografia",
        "mandato_status",
        "mandato_observacao",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("mandato_inicio", "mandato_fim", mode="before")
    @classmethod
    def _normalize_year_fields(cls, value: Any) -> int:
        text = clean_text(value)
        if text is None:
            raise ValueError("ano do mandato e obrigatorio")
        return int(text)

    @field_validator("id_origem", mode="before")
    @classmethod
    def _normalize_id_origem(cls, value: Any) -> int | None:
        text = clean_text(value)
        if text is None:
            return None
        return int(text)
