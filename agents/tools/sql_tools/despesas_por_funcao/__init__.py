"""Ferramentas SQL publicas do dominio `despesas-por-funcao`."""

from .agregar_despesas_por_funcao_query import agregar_despesas_por_funcao
from .consultar_despesas_por_funcao_query import consultar_despesas_por_funcao


__all__ = [
    "consultar_despesas_por_funcao",
    "agregar_despesas_por_funcao",
]
