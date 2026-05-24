"""Schemas de saida compartilhados pelas tools de servidores."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from .base import ServidoresToolBaseSchema


class ServidorToolItem(ServidoresToolBaseSchema):
    id: int
    nome: str
    cargo: str
    secretaria: str
    salario_base: float | None = None
    mes_de_referencia: date


class ServidoresToolResponse(ServidoresToolBaseSchema):
    query: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    mes_de_referencia: date | None = None
    total: int
    resultados: list[ServidorToolItem] = Field(default_factory=list)
    secretarias_correspondentes: list[str] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None


class QuantidadeServidoresPorSecretariaResponse(ServidoresToolBaseSchema):
    query: str | None = None
    mes_de_referencia: date | None = None
    total_servidores: int
    secretarias_correspondentes: list[str] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None


class SecretariaRankingItem(ServidoresToolBaseSchema):
    secretaria: str
    total_servidores: int


class SecretariasRankingToolResponse(ServidoresToolBaseSchema):
    mes_de_referencia: date | None = None
    total: int
    resultados: list[SecretariaRankingItem] = Field(default_factory=list)
    mensagem: str | None = None
    sugestao: str | None = None


class SecretariaComMaisServidoresResponse(ServidoresToolBaseSchema):
    mes_de_referencia: date | None = None
    secretaria: str | None = None
    total_servidores: int = 0
    mensagem: str | None = None
    sugestao: str | None = None
