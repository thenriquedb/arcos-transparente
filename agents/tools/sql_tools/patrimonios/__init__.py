"""Ferramentas SQL publicas do dominio de patrimonios."""

from .agregar_patrimonios_query import agregar_patrimonios
from .consultar_patrimonios_query import consultar_patrimonios


__all__ = [
    "agregar_patrimonios",
    "consultar_patrimonios",
]
