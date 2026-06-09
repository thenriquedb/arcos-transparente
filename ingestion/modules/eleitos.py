"""Modulo de ingestao adapter for eleitos."""

from __future__ import annotations

from database.models import Eleito

from .adapters import build_model_loader_adapter
from .discovery import discover_eleitos_files

ADAPTER = build_model_loader_adapter(
    "eleitos",
    discover_files=discover_eleitos_files,
    parser_attr="eleitos_parser",
    model=Eleito,
)
