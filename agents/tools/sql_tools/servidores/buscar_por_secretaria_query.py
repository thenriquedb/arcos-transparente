"""Tool para buscar servidores por secretaria."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agents.tools.registry import register
from database import session as session_manager

from .shared.params import BuscarServidorPorSecretariaParams
from .shared.responses import ServidoresToolResponse
from .shared.runtime import obter_mes_de_referencia_mais_recente, resposta_sem_resultados, serializar_servidor
from .shared.secretaria_queries import (
    contar_servidores_por_secretaria_na_competencia,
    listar_secretarias_correspondentes,
    listar_servidores_por_secretaria_na_competencia,
)


@register(name="buscar_servidores_por_secretaria")
def buscar_servidores_por_secretaria(
    secretaria: str,
    limite: int = 10,
) -> dict[str, Any]:
    """
    Busca servidores por secretaria.

    Examples:
      'quais servidores trabalham na Secretaria de Educação',
      'me mostre os servidores da Secretaria de Saúde'.

    Args:
        secretaria (str): O nome ou parte do nome da secretaria a ser buscada.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com a query, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorSecretariaParams.model_validate(
            {"secretaria": secretaria, "limite": limite}
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.secretaria:
        return resposta_sem_resultados(
            query=secretaria,
            mensagem="Informe uma secretaria para realizar a busca.",
        )

    termo_normalizado = params.secretaria.lower()

    with session_manager.get_session() as session:
        mes_de_referencia = obter_mes_de_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return resposta_sem_resultados(
                query=params.secretaria,
                mensagem="Nao ha registros de servidores disponiveis para consulta.",
            )

        secretarias_correspondentes = listar_secretarias_correspondentes(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )
        if not secretarias_correspondentes:
            return resposta_sem_resultados(
                query=params.secretaria,
                mes_de_referencia=mes_de_referencia,
                sugestao=(
                    f"Nenhum servidor encontrado para a secretaria '{params.secretaria}'."
                ),
            )

        total_servidores = contar_servidores_por_secretaria_na_competencia(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )
        servidores = listar_servidores_por_secretaria_na_competencia(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
            limite=params.limite,
        )

    mensagem = None
    if total_servidores > len(servidores):
        mensagem = (
            f"Mostrando {len(servidores)} de {total_servidores} servidores "
            "no mes mais recente com dados."
        )

    return ServidoresToolResponse(
        query=params.secretaria,
        mes_de_referencia=mes_de_referencia,
        total=total_servidores,
        resultados=[serializar_servidor(servidor) for servidor in servidores],
        secretarias_correspondentes=secretarias_correspondentes,
        mensagem=mensagem,
    ).model_dump(mode="json")
