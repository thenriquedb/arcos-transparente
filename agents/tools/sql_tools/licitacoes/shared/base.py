"""Schemas base das tools de licitacoes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LicitacoesToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de licitacoes."""

    model_config = ConfigDict(extra="ignore")
