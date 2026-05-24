"""Tool para ranking de secretarias por quantidade de servidores."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import register
from database import session as session_manager
from database.models import Servidor

from .shared.params import RankingSecretariasParams
from .shared.responses import SecretariaRankingItem, SecretariasRankingToolResponse
from .shared.runtime import obter_mes_de_referencia_mais_recente


def _buscar_ranking_secretarias_na_competencia(
    session,
    *,
    competencia_referencia,
    limite: int,
) -> list[tuple[str, int]]:
    total_servidores = func.count(func.distinct(func.lower(Servidor.nome))).label(
        "total_servidores"
    )
    return session.execute(
        select(Servidor.secretaria, total_servidores)
        .where(Servidor.competencia_referencia == competencia_referencia)
        .group_by(Servidor.secretaria)
        .order_by(total_servidores.desc(), Servidor.secretaria.asc())
        .limit(limite)
    ).all()


@register(name="listar_secretarias_por_quantidade_de_servidores")
def listar_secretarias_por_quantidade_de_servidores(
    limite: int = 10,
) -> dict[str, Any]:
    """
    Lista as secretarias com mais servidores no mes mais recente com dados.

    Examples:
      'quais secretarias tem mais funcionarios?',
      'top 5 secretarias por quantidade de servidores'.

    Args:
        limite (int): Numero maximo de secretarias no ranking.
    Returns:
        dict com o mes usado e o ranking de secretarias.
    """

    try:
        params = RankingSecretariasParams.model_validate({"limite": limite})
    except ValidationError as exc:
        return SecretariasRankingToolResponse(
            total=0,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        mes_de_referencia = obter_mes_de_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return SecretariasRankingToolResponse(
                total=0,
                mensagem="Nao ha registros de servidores disponiveis para consulta.",
            ).model_dump(mode="json")

        ranking = _buscar_ranking_secretarias_na_competencia(
            session,
            competencia_referencia=mes_de_referencia,
            limite=params.limite,
        )

    if not ranking:
        return SecretariasRankingToolResponse(
            mes_de_referencia=mes_de_referencia,
            total=0,
            sugestao="Nenhuma secretaria encontrada no mes mais recente com dados.",
        ).model_dump(mode="json")

    return SecretariasRankingToolResponse(
        mes_de_referencia=mes_de_referencia,
        total=len(ranking),
        resultados=[
            SecretariaRankingItem(
                secretaria=secretaria,
                total_servidores=total_servidores,
            )
            for secretaria, total_servidores in ranking
        ],
    ).model_dump(mode="json")
