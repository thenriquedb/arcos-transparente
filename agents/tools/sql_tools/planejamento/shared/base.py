"""Base Pydantic para tools de planejamento."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PlanejamentoToolBaseSchema(BaseModel):
    """Config comum dos schemas das tools de planejamento."""

    model_config = ConfigDict(extra="ignore")
