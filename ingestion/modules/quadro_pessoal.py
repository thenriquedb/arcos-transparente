"""Modulo de ingestao adapter for quadro de pessoal."""

from __future__ import annotations

from database.models import QuadroPessoal

from .adapters import build_model_loader_adapter
from .discovery import discover_quadro_pessoal_files

ADAPTER = build_model_loader_adapter(
    "quadro_pessoal",
    discover_files=discover_quadro_pessoal_files,
    parser_attr="quadro_pessoal_parser",
    model=QuadroPessoal,
)
