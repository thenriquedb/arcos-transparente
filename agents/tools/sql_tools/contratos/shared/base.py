"""Schemas base das tools de contratos."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ContratosToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de contratos."""

    model_config = ConfigDict(extra="ignore")
