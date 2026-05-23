"""Tools SQL para consultas de folha e servidores."""

from __future__ import annotations

from datetime import date

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from agents.tools.sql_tools.folha_pagamento_schemas import (
    BuscarHistoricoPagamentosServidorParams,
    HistoricoPagamentosServidorItem,
    HistoricoPagamentosServidorResponse,
    PagamentoMensalItem,
)
from database.models import FolhaPagamentoRegistro, FolhaServidor
from database.session import get_session
from shared.utils.decimal_to_float import decimal_to_float


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
        return _resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.nome:
        return _resposta_sem_resultados(
            query=nome,
            mensagem="Informe um nome de servidor para realizar a busca.",
        )

    termo_normalizado = params.nome.lower()

    with get_session() as session:
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
        return _resposta_sem_resultados(
            query=params.nome,
            sugestao=(
                f"Nenhum servidor encontrado com '{params.nome}'. "
                "Tente buscar por partes do nome, ex: só o sobrenome."
            ),
        )

    resultados = [
        _serializar_servidor(servidor, params.max_meses) for servidor in servidores
    ]

    return HistoricoPagamentosServidorResponse(
        query=params.nome,
        total=len(resultados),
        resultados=resultados,
    ).model_dump(mode="json")


def _resposta_sem_resultados(
    *,
    query: str | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, Any]:
    return HistoricoPagamentosServidorResponse(
        query=query,
        total=0,
        resultados=[],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")


def _serializar_servidor(
    servidor: FolhaServidor,
    max_meses: int,
) -> dict[str, Any]:
    pagamentos = sorted(
        servidor.pagamentos,
        key=lambda registro: (
            registro.competencia_ano,
            registro.competencia_mes_num,
        ),
        reverse=True,
    )
    pagamentos_limitados = pagamentos[:max_meses]
    pagamento_recente = pagamentos_limitados[0] if pagamentos_limitados else None

    payload = HistoricoPagamentosServidorItem.model_validate(
        {
            "folha_servidor_id": servidor.id,
            "nome": servidor.nome,
            "cargo_atual": (
                pagamento_recente.cargo.nome
                if pagamento_recente and pagamento_recente.cargo
                else None
            ),
            "setor_atual": (
                pagamento_recente.lotacao.nome
                if pagamento_recente and pagamento_recente.lotacao
                else None
            ),
            "mes_de_referencia_do_servidor": (
                servidor.servidor_canonico.competencia_referencia
                if servidor.servidor_canonico
                and servidor.servidor_canonico.competencia_referencia
                else None
            ),
            "total_meses_considerados": len(pagamentos_limitados),
            "pagamentos": [
                PagamentoMensalItem(
                    ano=registro.competencia_ano,
                    mes_num=registro.competencia_mes_num,
                    mes_nome=registro.competencia_mes_nome,
                    cargo=registro.cargo.nome if registro.cargo else None,
                    setor=registro.lotacao.nome if registro.lotacao else None,
                    salario_base=decimal_to_float(registro.salario_base),
                    ganhos=decimal_to_float(registro.proventos),
                    adicionais=decimal_to_float(registro.vantagens),
                    total_bruto=decimal_to_float(
                        registro.vencimentos_totais
                    ),
                    descontos=decimal_to_float(registro.descontos),
                    valor_recebido=decimal_to_float(registro.liquido),
                )
                for registro in pagamentos_limitados
            ],
            "total_recebido": decimal_to_float(
                sum(
                    registro.liquido
                    for registro in pagamentos_limitados
                    if registro.liquido is not None
                )
            ),
            "nota": (
                f"Dados consultados em {date.today().isoformat()}. "
                f"Historico limitado aos ultimos {max_meses} meses de pagamento."
            ),
        }
    )
    return payload.model_dump(mode="json")
