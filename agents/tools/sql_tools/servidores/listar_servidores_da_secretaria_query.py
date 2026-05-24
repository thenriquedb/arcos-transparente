"""Tool para listar servidores de uma secretaria."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import register

from .buscar_por_secretaria_query import buscar_servidores_por_secretaria


@register(name="listar_servidores_da_secretaria")
def listar_servidores_da_secretaria(
    secretaria: str,
    limite: int = 50,
) -> dict[str, Any]:
    """
    Lista servidores da secretaria no mes mais recente com dados.

    Examples:
      'liste todos os funcionarios da educacao',
      'me mostre quem trabalha na saude'.

    Args:
        secretaria (str): Nome ou parte do nome da secretaria.
        limite (int): Numero maximo de resultados retornados.
    Returns:
        dict com total de servidores e a lista limitada de resultados.
    """

    return buscar_servidores_por_secretaria(secretaria=secretaria, limite=limite)
