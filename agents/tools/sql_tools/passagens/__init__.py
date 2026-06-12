"""Ferramentas SQL publicas do dominio de passagens."""

from .agregar_passagens_query import agregar_passagens
from .consultar_passagens_query import consultar_passagens


__all__ = [
    "agregar_passagens",
    "consultar_passagens",
]
