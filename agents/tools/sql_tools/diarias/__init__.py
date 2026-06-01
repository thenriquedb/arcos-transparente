"""Ferramentas SQL publicas do dominio de diarias."""

from .agregar_diarias_query import agregar_diarias
from .consultar_diarias_query import consultar_diarias

__all__ = [
    "agregar_diarias",
    "consultar_diarias",
]
