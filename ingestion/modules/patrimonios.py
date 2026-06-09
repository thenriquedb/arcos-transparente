"""Modulo de ingestao adapter for patrimonios."""

from __future__ import annotations

from database.models import Patrimonio

from .adapters import build_model_loader_adapter
from .discovery import discover_patrimonios_files

ADAPTER = build_model_loader_adapter(
    "patrimonios",
    discover_files=discover_patrimonios_files,
    parser_attr="patrimonios_parser",
    model=Patrimonio,
)
