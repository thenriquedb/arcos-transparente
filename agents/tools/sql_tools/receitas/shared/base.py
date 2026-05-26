"""Base Pydantic para tools de receitas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReceitasToolBaseSchema(BaseModel):
    """Config comum dos schemas das tools de receitas."""

    model_config = ConfigDict(extra="ignore")
