from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select

from agents.tools.sql_tools.servidores_schemas import (
    BuscarServidorPorCargoParams,
    BuscarServidorPorNomeParams,
    BuscarServidorPorPeriodoParams,
    BuscarServidorPorSecretariaParams,
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
            "competencia_referencia": servidor.competencia_referencia,
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


def _resposta_sem_resultados(
    *,
    query: str | None = None,
    data_inicio: Any | None = None,
    data_fim: Any | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, Any]:
    return ServidoresToolResponse(
        query=query,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total=0,
        resultados=[],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")


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

    servidores = _executar_busca_textual(
        Servidor.secretaria, params.secretaria, params.limite
    )
    if not servidores:
        return _resposta_sem_resultados(
            query=params.secretaria,
            sugestao=(
                f"Nenhum servidor encontrado para a secretaria '{params.secretaria}'."
            ),
        )

    return ServidoresToolResponse(
        query=params.secretaria,
        total=len(servidores),
        resultados=[_serializar_servidor(servidor) for servidor in servidores],
    ).model_dump(mode="json")


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


def buscar_servidores_por_competencia_no_periodo(
    data_inicio: str, data_fim: str, limite: int = 10
) -> dict[str, Any]:
    """
    Busca servidores com registros em um período de competência específico.

    Examples:
        'quais servidores aparecem entre 01/01/2025 e 31/03/2025',
        'me mostre os servidores com competência em 2025-02-01'.

    Args:
        data_inicio (str): Data inicial da competência no formato `DD/MM/YYYY` ou ISO.
        data_fim (str): Data final da competência no formato `DD/MM/YYYY` ou ISO.
        limite (int): O número máximo de resultados a serem retornados.
    Returns:
        dict com o periodo consultado, total e resultados padronizados.
    """
    try:
        params = BuscarServidorPorPeriodoParams.model_validate(
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


def buscar_servidores_admitidos_no_periodo(
    data_inicio: str, data_fim: str, limite: int = 10
) -> dict[str, Any]:
    """Alias de compatibilidade para busca por competencia no periodo."""

    return buscar_servidores_por_competencia_no_periodo(
        data_inicio=data_inicio,
        data_fim=data_fim,
        limite=limite,
    )
