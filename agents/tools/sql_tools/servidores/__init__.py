"""Ferramentas SQL do dominio de servidores."""

from .buscar_por_cargo_query import buscar_servidores_por_cargo
from .buscar_por_mes_de_referencia_no_periodo_query import (
    buscar_servidores_por_mes_de_referencia_no_periodo,
)
from .buscar_por_nome_query import buscar_servidores_por_nome
from .buscar_por_secretaria_query import buscar_servidores_por_secretaria
from .buscar_secretaria_com_mais_servidores_query import (
    buscar_secretaria_com_mais_servidores,
)
from .contar_servidores_por_secretaria_query import contar_servidores_por_secretaria
from .listar_maiores_salarios_query import listar_maiores_salarios
from .listar_secretarias_por_quantidade_de_servidores_query import (
    listar_secretarias_por_quantidade_de_servidores,
)
from .listar_servidores_da_secretaria_query import listar_servidores_da_secretaria

__all__ = [
    "buscar_secretaria_com_mais_servidores",
    "buscar_servidores_por_cargo",
    "buscar_servidores_por_mes_de_referencia_no_periodo",
    "buscar_servidores_por_nome",
    "buscar_servidores_por_secretaria",
    "contar_servidores_por_secretaria",
    "listar_maiores_salarios",
    "listar_secretarias_por_quantidade_de_servidores",
    "listar_servidores_da_secretaria",
]
