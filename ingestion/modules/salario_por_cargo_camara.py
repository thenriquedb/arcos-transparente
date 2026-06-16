"""Modulo de ingestao adapter para tabela de remuneracao de cargos da Camara."""

from __future__ import annotations

from database.models import SalarioPorCargoCamara

from .adapters import build_model_loader_adapter
from .discovery import discover_salario_por_cargo_camara_files


ADAPTER = build_model_loader_adapter(
    "salario_por_cargo_camara",
    discover_files=discover_salario_por_cargo_camara_files,
    parser_attr="salario_por_cargo_camara_parser",
    model=SalarioPorCargoCamara,
)
