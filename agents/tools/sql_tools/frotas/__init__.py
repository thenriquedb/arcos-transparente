"""Ferramentas SQL publicas do dominio de frotas."""

from .agregar_despesas_frota_query import agregar_despesas_frota
from .agregar_frota_query import agregar_frota
from .consultar_despesas_frota_query import consultar_despesas_frota
from .consultar_frota_query import consultar_frota


__all__ = [
    "agregar_despesas_frota",
    "agregar_frota",
    "consultar_despesas_frota",
    "consultar_frota",
]
