"""Schemas de entrada compartilhados pelas tools de folha."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from shared.utils.validation import clean_text, normalize_limit

from .base import FolhaPagamentoToolBaseSchema


class BuscarHistoricoPagamentosServidorParams(FolhaPagamentoToolBaseSchema):
    nome: str | None
    limite: int = 10
    max_meses: int = 24

    @field_validator("nome", mode="before")
    @classmethod
    def _normalize_nome(cls, value: Any) -> str | None:
        return clean_text(value)

    @field_validator("limite", mode="before")
    @classmethod
    def _normalize_limite(cls, value: Any) -> int:
        return normalize_limit(value, maximum=50)

    @field_validator("max_meses", mode="before")
    @classmethod
    def _normalize_max_meses(cls, value: Any) -> int:
        return normalize_limit(value, maximum=48)
