"""Tool para listar os maiores salarios dos servidores."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.registry import register
from database import session as session_manager
from database.models import Servidor

from .shared.params import RankingSalariosParams
from .shared.responses import ServidoresToolResponse
from .shared.runtime import obter_mes_de_referencia_mais_recente, resposta_sem_resultados, serializar_servidor


def _contar_servidores_com_salario_na_competencia(
    session,
    *,
    competencia_referencia,
) -> int:
    return session.execute(
        select(func.count())
        .select_from(Servidor)
        .where(Servidor.competencia_referencia == competencia_referencia)
        .where(Servidor.salario_base.is_not(None))
    ).scalar_one()


def _listar_maiores_salarios_na_competencia(
    session,
    *,
    competencia_referencia,
    limite: int,
) -> list[Servidor]:
    return (
        session.execute(
            select(Servidor)
            .where(Servidor.competencia_referencia == competencia_referencia)
            .where(Servidor.salario_base.is_not(None))
            .order_by(Servidor.salario_base.desc(), Servidor.nome.asc())
            .limit(limite)
        )
        .scalars()
        .all()
    )


@register(name="listar_maiores_salarios")
def listar_maiores_salarios(limite: int = 10) -> dict[str, Any]:
    """
    Lista os servidores com os maiores salarios base no mes mais recente com dados.

    Examples:
      'quais os 10 maiores salarios da prefeitura?',
      'me mostre os maiores salarios dos servidores'.

    Args:
        limite (int): Numero maximo de resultados retornados.
    Returns:
        dict com o mes usado, total encontrado e resultados ordenados do maior
        salario para o menor.
    """

    try:
        params = RankingSalariosParams.model_validate({"limite": limite})
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    with session_manager.get_session() as session:
        mes_de_referencia = obter_mes_de_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return resposta_sem_resultados(
                mensagem="Nao ha registros de servidores disponiveis para consulta."
            )

        total_servidores = _contar_servidores_com_salario_na_competencia(
            session,
            competencia_referencia=mes_de_referencia,
        )
        if total_servidores == 0:
            return resposta_sem_resultados(
                query="maiores salarios",
                mes_de_referencia=mes_de_referencia,
                sugestao="Nenhum salario cadastrado no mes mais recente com dados.",
            )

        servidores = _listar_maiores_salarios_na_competencia(
            session,
            competencia_referencia=mes_de_referencia,
            limite=params.limite,
        )

    mensagem = None
    if total_servidores > len(servidores):
        mensagem = (
            f"Mostrando {len(servidores)} de {total_servidores} servidores "
            "com salario no mes mais recente com dados."
        )

    return ServidoresToolResponse(
        query="maiores salarios",
        mes_de_referencia=mes_de_referencia,
        total=total_servidores,
        resultados=[serializar_servidor(servidor) for servidor in servidores],
        mensagem=mensagem,
    ).model_dump(mode="json")
