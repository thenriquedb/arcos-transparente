"""Tool para descobrir a secretaria com mais servidores."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import register

from .listar_secretarias_por_quantidade_de_servidores_query import (
    listar_secretarias_por_quantidade_de_servidores,
)
from .shared.responses import SecretariaComMaisServidoresResponse


@register(name="buscar_secretaria_com_mais_servidores")
def buscar_secretaria_com_mais_servidores() -> dict[str, Any]:
    """
    Retorna a secretaria com mais servidores no mes mais recente com dados.

    Example:
      'qual secretaria tem mais funcionarios?'.

    Returns:
        dict com a secretaria lider no ranking e seu total de servidores.
    """

    ranking = listar_secretarias_por_quantidade_de_servidores(limite=1)
    if ranking["total"] == 0:
        return SecretariaComMaisServidoresResponse(
            mensagem=ranking.get("mensagem"),
            sugestao=ranking.get("sugestao"),
        ).model_dump(mode="json")

    lider = ranking["resultados"][0]
    return SecretariaComMaisServidoresResponse(
        mes_de_referencia=ranking.get("mes_de_referencia"),
        secretaria=lider["secretaria"],
        total_servidores=lider["total_servidores"],
    ).model_dump(mode="json")
