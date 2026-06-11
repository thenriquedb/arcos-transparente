"""Ferramentas SQL publicas do dominio de quadro de pessoal."""

from .agregar_quadro_pessoal_query import agregar_quadro_pessoal
from .consultar_quadro_pessoal_query import consultar_quadro_pessoal


__all__ = [
    "agregar_quadro_pessoal",
    "consultar_quadro_pessoal",
]
