"""Modulo de ingestao adapter for servidores JSON snapshots."""

from __future__ import annotations

from database.models import Servidor

from .adapters import build_model_loader_adapter
from .discovery import discover_servidores_files

ADAPTER = build_model_loader_adapter(
    "servidores",
    discover_files=discover_servidores_files,
    parser_attr="servidores_parser",
    model=Servidor,
)
