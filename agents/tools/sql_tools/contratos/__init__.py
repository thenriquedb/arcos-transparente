"""Ferramentas SQL publicas do dominio de contratos."""

from .agregar_contratos_query import agregar_contratos
from .consultar_contratos_query import consultar_contratos


__all__ = [
    "consultar_contratos",
    "agregar_contratos",
]
