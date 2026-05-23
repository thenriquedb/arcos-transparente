from datetime import date
from typing import Any

from agents.tools.registry import register
from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.sql_tools.servidores_schemas import (
    BuscarServidorPorCargoParams,
    BuscarServidorPorMesDeReferenciaParams,
    BuscarServidorPorNomeParams,
    BuscarServidorPorSecretariaParams,
    QuantidadeServidoresPorSecretariaResponse,
    RankingSecretariasParams,
    SecretariaComMaisServidoresResponse,
    SecretariaRankingItem,
    SecretariasRankingToolResponse,
    ServidoresToolResponse,
    ServidorToolItem,
)
from database.models import Servidor
from database.session import get_session
from shared.utils.decimal_to_float import decimal_to_float


def _serializar_servidor(servidor: Servidor) -> dict[str, Any]:
    """Serializa o modelo ORM em payload padronizado para as tools."""

    payload = ServidorToolItem.model_validate(
        {
            "id": servidor.id,
            "nome": servidor.nome,
            "cargo": servidor.cargo,
            "secretaria": servidor.secretaria,
            "salario_base": decimal_to_float(servidor.salario_base),
            "mes_de_referencia": servidor.competencia_referencia,
        }
    )
    return payload.model_dump(mode="json")


def _executar_busca_textual(
    campo,
    termo: str,
    limite: int,
) -> list[Servidor]:
    termo_normalizado = termo.lower()

    with get_session() as session:
        return (
            session.execute(
                select(Servidor)
                .where(func.lower(campo).like(f"%{termo_normalizado}%"))
                .order_by(Servidor.nome.asc())
                .limit(limite)
            )
            .scalars()
            .all()
        )


def _obter_competencia_referencia_mais_recente(session) -> date | None:
    return session.execute(
        select(func.max(Servidor.competencia_referencia))
    ).scalar_one_or_none()


def _construir_subquery_secretaria(
    *,
    termo_normalizado: str,
    competencia_referencia: date,
):
    return (
        select(func.max(Servidor.id).label("id"))
        .where(Servidor.competencia_referencia == competencia_referencia)
        .where(func.lower(Servidor.secretaria).like(f"%{termo_normalizado}%"))
        .group_by(func.lower(Servidor.nome), func.lower(Servidor.secretaria))
        .subquery()
    )


def _listar_secretarias_correspondentes(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
) -> list[str]:
    return (
        session.execute(
            select(Servidor.secretaria)
            .where(Servidor.competencia_referencia == competencia_referencia)
            .where(func.lower(Servidor.secretaria).like(f"%{termo_normalizado}%"))
            .group_by(Servidor.secretaria)
            .order_by(Servidor.secretaria.asc())
        )
        .scalars()
        .all()
    )


def _contar_servidores_por_secretaria_na_competencia(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
) -> int:
    subquery = _construir_subquery_secretaria(
        termo_normalizado=termo_normalizado,
        competencia_referencia=competencia_referencia,
    )
    return session.execute(select(func.count()).select_from(subquery)).scalar_one()


def _listar_servidores_por_secretaria_na_competencia(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
    limite: int,
) -> list[Servidor]:
    subquery = _construir_subquery_secretaria(
        termo_normalizado=termo_normalizado,
        competencia_referencia=competencia_referencia,
    )
    return (
        session.execute(
            select(Servidor)
            .join(subquery, Servidor.id == subquery.c.id)
            .order_by(Servidor.secretaria.asc(), Servidor.nome.asc())
            .limit(limite)
        )
        .scalars()
        .all()
    )


def _buscar_ranking_secretarias_na_competencia(
    session,
    *,
    competencia_referencia: date,
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


def _resposta_sem_resultados(
    *,
    query: str | None = None,
    data_inicio: Any | None = None,
    data_fim: Any | None = None,
    mes_de_referencia: Any | None = None,
    secretarias_correspondentes: list[str] | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, Any]:
    return ServidoresToolResponse(
        query=query,
        data_inicio=data_inicio,
        data_fim=data_fim,
        mes_de_referencia=mes_de_referencia,
        total=0,
        resultados=[],
        secretarias_correspondentes=secretarias_correspondentes or [],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")

@register(name="buscar_servidores_por_nome")
def buscar_servidores_por_nome(nome: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca um servidor pelo nome ou parte do nome.

    Examples:
      'qual o salário de João Silva',
      'me mostre os dados de Maria Souza'.

    Args:
        nome (str): O nome ou parte do nome do servidor a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com a query, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorNomeParams.model_validate(
            {"nome": nome, "limite": limite}
        )
    except ValidationError as exc:
        return _resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.nome:
        return _resposta_sem_resultados(
            query=nome,
            mensagem="Informe um nome de servidor para realizar a busca.",
        )

    palavras = params.nome.lower().split()
    filtros = [func.lower(Servidor.nome).like(f"%{palavra}%") for palavra in palavras]

    with get_session() as session:
        servidores = (
            session.execute(
                select(Servidor)
                .where(*filtros)
                .order_by(Servidor.nome.asc())
                .limit(params.limite)
            )
            .scalars()
            .all()
        )

    if not servidores:
        return _resposta_sem_resultados(
            query=params.nome,
            sugestao=(
                f"Nenhum servidor encontrado com '{params.nome}'. "
                "Tente buscar por partes do nome, ex: só o sobrenome."
            ),
        )

    return ServidoresToolResponse(
        query=params.nome,
        total=len(servidores),
        resultados=[_serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")


@register(name="buscar_servidores_por_secretaria")
def buscar_servidores_por_secretaria(
    secretaria: str, limite: int = 10
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
        return _resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.secretaria:
        return _resposta_sem_resultados(
            query=secretaria,
            mensagem="Informe uma secretaria para realizar a busca.",
        )

    termo_normalizado = params.secretaria.lower()

    with get_session() as session:
        mes_de_referencia = _obter_competencia_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return _resposta_sem_resultados(
                query=params.secretaria,
                mensagem="Nao ha registros de servidores disponiveis para consulta.",
            )

        secretarias_correspondentes = _listar_secretarias_correspondentes(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )
        if not secretarias_correspondentes:
            return _resposta_sem_resultados(
                query=params.secretaria,
                mes_de_referencia=mes_de_referencia,
                sugestao=(
                    f"Nenhum servidor encontrado para a secretaria '{params.secretaria}'."
                ),
            )

        total_servidores = _contar_servidores_por_secretaria_na_competencia(
            session,
            termo_normalizado=termo_normalizado,
            competencia_referencia=mes_de_referencia,
        )
        servidores = _listar_servidores_por_secretaria_na_competencia(
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
        resultados=[_serializar_servidor(servidor) for servidor in servidores],
        secretarias_correspondentes=secretarias_correspondentes,
        mensagem=mensagem,
    ).model_dump(mode="json")


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

    with get_session() as session:
        mes_de_referencia = _obter_competencia_referencia_mais_recente(session)
        if mes_de_referencia is None:
            return QuantidadeServidoresPorSecretariaResponse(
                query=params.secretaria,
                total_servidores=0,
                mensagem="Nao ha registros de servidores disponiveis para consulta.",
            ).model_dump(mode="json")

        secretarias_correspondentes = _listar_secretarias_correspondentes(
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

        total_servidores = _contar_servidores_por_secretaria_na_competencia(
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

@register(name="buscar_servidores_por_cargo")
def buscar_servidores_por_cargo(cargo: str, limite: int = 10) -> dict[str, Any]:
    """
    Busca servidores por cargo.

    Examples:
        'quais servidores ocupam o cargo de Professor',
        'me mostre os servidores que são Médicos'.

    Args:
        cargo (str): O nome ou parte do nome do cargo a ser buscado.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com a query, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorCargoParams.model_validate(
            {"cargo": cargo, "limite": limite}
        )
    except ValidationError as exc:
        return _resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.cargo:
        return _resposta_sem_resultados(
            query=cargo,
            mensagem="Informe um cargo para realizar a busca.",
        )

    servidores = _executar_busca_textual(Servidor.cargo, params.cargo, params.limite)
    if not servidores:
        return _resposta_sem_resultados(
            query=params.cargo,
            sugestao=f"Nenhum servidor encontrado para o cargo '{params.cargo}'.",
        )

    return ServidoresToolResponse(
        query=params.cargo,
        total=len(servidores),
        resultados=[_serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")


@register(name="buscar_servidores_por_mes_de_referencia_no_periodo")
def buscar_servidores_por_mes_de_referencia_no_periodo(
    data_inicio: str, data_fim: str, limite: int = 10
) -> dict[str, Any]:
    """
    Busca servidores com registros em um periodo especifico.

    Examples:
        'quais servidores aparecem entre 01/01/2025 e 31/03/2025',
        'me mostre os servidores com mes de referencia em 2025-02-01'.

    Args:
        data_inicio (str): Data inicial do periodo no formato `DD/MM/YYYY` ou ISO.
        data_fim (str): Data final do periodo no formato `DD/MM/YYYY` ou ISO.
        limite (int): O numero maximo de resultados a serem retornados.
    Returns:
        dict com o periodo consultado, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorMesDeReferenciaParams.model_validate(
            {
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "limite": limite,
            }
        )
    except ValidationError as exc:
        return _resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    with get_session() as session:
        servidores = (
            session.execute(
                select(Servidor)
                .where(
                    Servidor.competencia_referencia.between(
                        params.data_inicio,
                        params.data_fim,
                    )
                )
                .order_by(
                    Servidor.competencia_referencia.asc(),
                    Servidor.nome.asc(),
                )
                .limit(params.limite)
            )
            .scalars()
            .all()
        )

    if not servidores:
        return _resposta_sem_resultados(
            data_inicio=params.data_inicio,
            data_fim=params.data_fim,
            sugestao="Nenhum servidor encontrado no periodo informado.",
        )

    return ServidoresToolResponse(
        data_inicio=params.data_inicio,
        data_fim=params.data_fim,
        total=len(servidores),
        resultados=[_serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")


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

    with get_session() as session:
        mes_de_referencia = _obter_competencia_referencia_mais_recente(session)
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
