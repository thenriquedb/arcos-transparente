"""Schemas base das tools de servidores."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ServidoresToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de servidores."""

    model_config = ConfigDict(extra="ignore")
