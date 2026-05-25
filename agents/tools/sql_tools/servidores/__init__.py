"""Ferramentas SQL publicas do dominio de servidores."""

from .agregar_servidores_query import agregar_servidores
from .consultar_servidores_query import consultar_servidores

__all__ = [
    "agregar_servidores",
    "consultar_servidores",
]
