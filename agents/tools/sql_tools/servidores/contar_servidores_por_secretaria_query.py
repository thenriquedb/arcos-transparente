"""Tool para contar servidores por secretaria."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import register
from database import session as session_manager

from .shared.params import BuscarServidorPorSecretariaParams
from .shared.responses import QuantidadeServidoresPorSecretariaResponse
from .shared.runtime import obter_mes_de_referencia_mais_recente
from .shared.secretaria_queries import (
    contar_servidores_por_secretaria_na_competencia,
    listar_secretarias_correspondentes,
)


@register(name="contar_servidores_por_secretaria")
def contar_servidores_por_secretaria(secretaria: str) -> dict[str, Any]:
    """
    Conta quantos servidores existem em uma secretaria no mes mais recente com dados.

    Examples:
      'quantas pessoas trabalham na saude?',
      'quantos servidores tem na educacao?'.

    Args:
        secretaria (str): Nome ou parte do nome da secretaria.
    Returns:
        dict com o mes usado, secretarias correspondentes e total.
    """

    try:
        params = BuscarServidorPorSecretariaParams.model_validate(
            {"secretaria": secretaria, "limite": 1}
        )
    except ValidationError as exc:
        return QuantidadeServidoresPorSecretariaResponse(
            total_servidores=0,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    if not params.secretaria:
        return QuantidadeServidoresPorSecretariaResponse(
            query=secretaria,
            total_servidores=0,
            mensagem="Informe uma secretaria para realizar a contagem.",
        ).model_dump(mode="json")

    termo_normalizado = params.secretaria.lower()

    with session_manager.get_session() as session:
        mes_de_referencia = obter_mes_de_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return QuantidadeServidoresPorSecretariaResponse(
                query=params.secretaria,
                total_servidores=0,
                mensagem="Nao ha registros de servidores disponiveis para consulta.",
            ).model_dump(mode="json")

        secretarias_correspondentes = listar_secretarias_correspondentes(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )
        if not secretarias_correspondentes:
            return QuantidadeServidoresPorSecretariaResponse(
                query=params.secretaria,
                mes_de_referencia=mes_de_referencia,
                total_servidores=0,
                sugestao=(
                    f"Nenhum servidor encontrado para a secretaria '{params.secretaria}'."
                ),
            ).model_dump(mode="json")

        total_servidores = contar_servidores_por_secretaria_na_competencia(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )

    return QuantidadeServidoresPorSecretariaResponse(
        query=params.secretaria,
        mes_de_referencia=mes_de_referencia,
        total_servidores=total_servidores,
        secretarias_correspondentes=secretarias_correspondentes,
    ).model_dump(mode="json")
