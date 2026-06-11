"""Ferramentas SQL publicas do dominio de licitacoes."""

from .agregar_licitacoes_query import agregar_licitacoes
from .consultar_licitacoes_query import consultar_licitacoes


__all__ = [
    "agregar_licitacoes",
    "consultar_licitacoes",
]
