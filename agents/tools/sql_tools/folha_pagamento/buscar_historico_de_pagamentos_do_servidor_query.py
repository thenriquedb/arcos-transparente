"""Tool para buscar historico de pagamentos de um servidor."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.models import FolhaPagamentoRegistro, FolhaServidor

from .shared.params import BuscarHistoricoPagamentosServidorParams
from .shared.responses import HistoricoPagamentosServidorResponse
from .shared.runtime import resposta_sem_resultados, serializar_servidor


@register(
    name="buscar_historico_de_pagamentos_do_servidor",
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:history"],
)
def buscar_historico_de_pagamentos_do_servidor(
    nome: str,
    limite: int = 10,
    max_meses: int = 24,
) -> dict[str, Any]:
    """
    Busca um servidor publico pelo nome e retorna seu historico de pagamentos.

    Use quando o usuario perguntar sobre um servidor especifico pelo nome.
    Exemplos:
    - 'quanto Joao Silva recebeu em 2024?'
    - 'qual o salario de Maria Souza?'
    - 'quais cargos Pedro Oliveira ja ocupou?'
    - 'quanto foi pago a Jose no ultimo ano?'

    Retorna: cargo atual, setor atual, historico de salarios,
    ganhos, adicionais, descontos e valor recebido por mes.

    NAO use para perguntas sem nome especifico como 'quais servidores
    ganham mais de R$ 10 mil' ou 'quais cargos existem na prefeitura'.

    Args:
        nome: Nome ou parte do nome do servidor.
        limite: Numero maximo de resultados (padrao 10, maximo 50).
        max_meses: Numero maximo de meses do pagamento retornados por servidor.

    Returns:
        dict com 'total' e lista de 'resultados' contendo o historico
        de pagamentos em linguagem simples.
    """
    try:
        params = BuscarHistoricoPagamentosServidorParams.model_validate(
            {
                "nome": nome,
                "limite": limite,
                "max_meses": max_meses,
            }
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.nome:
        return resposta_sem_resultados(
            query=nome,
            mensagem="Informe um nome de servidor para realizar a busca.",
        )

    termo_normalizado = params.nome.lower()

    with session_manager.get_session() as session:
        servidores = (
            session.execute(
                select(FolhaServidor)
                .options(
                    joinedload(FolhaServidor.servidor_canonico),
                    joinedload(FolhaServidor.pagamentos).joinedload(
                        FolhaPagamentoRegistro.cargo
                    ),
                    joinedload(FolhaServidor.pagamentos).joinedload(
                        FolhaPagamentoRegistro.lotacao
                    ),
                )
                .where(func.lower(FolhaServidor.nome).like(f"%{termo_normalizado}%"))
                .order_by(FolhaServidor.nome.asc())
                .limit(params.limite)
            )
            .unique()
            .scalars()
            .all()
        )

    if not servidores:
        return resposta_sem_resultados(
            query=params.nome,
            sugestao=(
                f"Nenhum servidor encontrado com '{params.nome}'. "
                "Tente buscar por partes do nome, ex: só o sobrenome."
            ),
        )

    resultados = [
        serializar_servidor(servidor, params.max_meses) for servidor in servidores
    ]

    return HistoricoPagamentosServidorResponse(
        query=params.nome,
        total=len(resultados),
        resultados=resultados,
    ).model_dump(mode="json")
