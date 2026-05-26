"""Ferramentas SQL publicas do dominio de receitas."""

from .agregar_receitas_query import agregar_receitas
from .consultar_receitas_query import consultar_receitas

__all__ = [
    "agregar_receitas",
    "consultar_receitas",
]
