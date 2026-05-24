"""Schemas base das tools de folha de pagamento."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FolhaPagamentoToolBaseSchema(BaseModel):
    """Base de saneamento para entrada e saida das tools de folha."""

    model_config = ConfigDict(extra="ignore")
