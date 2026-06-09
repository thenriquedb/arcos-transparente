"""Modulo de ingestao adapter for planejamentos."""

from __future__ import annotations

from database.models import PlanejamentoDespesa

from .adapters import build_model_loader_adapter
from .discovery import discover_planejamentos_files

ADAPTER = build_model_loader_adapter(
    "planejamentos",
    discover_files=discover_planejamentos_files,
    parser_attr="planejamentos_parser",
    model=PlanejamentoDespesa,
)
