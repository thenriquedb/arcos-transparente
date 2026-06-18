"""Modulo de ingestao adapter para servidores da Camara Municipal (CSV)."""

from __future__ import annotations

from database.models import ServidorCamara

from .adapters import build_model_loader_adapter
from .discovery import discover_servidores_camara_files


ADAPTER = build_model_loader_adapter(
    "servidores_camara",
    discover_files=discover_servidores_camara_files,
    parser_attr="servidores_camara_csv_parser",
    model=ServidorCamara,
)
