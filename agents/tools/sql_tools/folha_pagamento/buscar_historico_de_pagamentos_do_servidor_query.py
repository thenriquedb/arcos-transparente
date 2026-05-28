"""Tool para buscar historico de pagamentos de um servidor."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from agents.tools.registry import PUBLIC_SCOPE, register
from database import session as session_manager
from database.session import _normalizar_texto
from database.models import FolhaPagamentoRegistro, FolhaServidor

from .shared.params import BuscarHistoricoPagamentosServidorParams
from .shared.responses import HistoricoPagamentosServidorResponse
from .shared.runtime import (
    resposta_sem_resultados,
    serializar_candidato_servidor,
    serializar_servidor,
)


@register(
    name="buscar_historico_de_pagamentos_do_servidor",
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:history"],
)
def buscar_historico_de_pagamentos_do_servidor(
    nome: str | None = None,
    folha_servidor_id: int | None = None,
    limite: int = 10,
    max_meses: int = 24,
) -> dict[str, Any]:
    """
    Busca um servidor por nome ou id e retorna seu historico mensal de pagamentos.

    Use esta tool quando a pergunta citar uma pessoa especifica e pedir salario,
    quanto recebeu, descontos, ganhos, adicionais ou a evolucao ao longo dos meses.
    Use tambem quando a pergunta for uma continuacao contextual, como
    "qual o salario dele?", "quanto ele recebe?" ou "qual o salario do prefeito?",
    resolvendo o nome completo a partir do historico da conversa antes de chamar
    esta tool.
    Se a pergunta mencionar apenas cargo politico, como "prefeito", "vice" ou
    "vereador", primeiro use `consultar_eleitos` para descobrir o `nome_completo`
    em exercicio; em seguida chame esta tool com esse nome completo.
    Para "qual o salario do prefeito?", use o `nome_completo` do prefeito em
    exercicio retornado por `consultar_eleitos`, nao solicite o nome ao usuario.
    NAO use para listar varios servidores, ordenar por salario ou contar pessoas;
    para isso use `consultar_servidores` ou `agregar_servidores`.
    NAO use para perguntas sobre vagas por regime; para isso use
    `consultar_quadro_pessoal` ou `agregar_quadro_pessoal`.

    Args:
        nome: Nome completo ou combinação com pelo menos dois termos do nome.
            Use quando a pergunta trouxer texto livre.
        folha_servidor_id: Identificador opcional para selecionar diretamente um
            candidato retornado por uma busca ambígua anterior.
        limite: Numero maximo de servidores retornados. Inteiro de 1 a 50.
        max_meses: Numero maximo de meses de pagamento por servidor.
            Inteiro de 1 a 48.

    Returns:
        dict com:
        - `query`: nome pesquisado apos saneamento.
        - `total`: quantidade de servidores encontrados ou candidatos quando a
          busca estiver ambigua.
        - `resultados`: lista de servidores; cada item pode incluir `nome`,
          `cargo_atual`, `setor_atual`, `mes_de_referencia_do_servidor`,
          `total_meses_considerados`, `pagamentos`, `total_recebido` e `nota`.
        - `candidatos`: lista de servidores possiveis quando a busca encontrar
          mais de uma pessoa. Nesse caso, `resultados` fica vazio.
        - `mensagem`: aviso de validacao ou orientacao de uso.
        - `sugestao`: dica quando nao houver correspondencia para o nome.
    """
    try:
        params = BuscarHistoricoPagamentosServidorParams.model_validate(
            {
                "nome": nome,
                "folha_servidor_id": folha_servidor_id,
                "limite": limite,
                "max_meses": max_meses,
            }
        )
    except ValidationError as exc:
        return resposta_sem_resultados(mensagem=f"Parametros invalidos: {exc}")

    if not params.nome and params.folha_servidor_id is None:
        return resposta_sem_resultados(
            query=nome,
            mensagem=(
                "Informe um nome de servidor ou selecione um `folha_servidor_id` "
                "para realizar a busca."
            ),
        )

    if params.folha_servidor_id is None and len(params.nome.split()) < 2:
        return resposta_sem_resultados(
            query=params.nome,
            mensagem=(
                "Informação insuficiente para consultar salário individual. "
                "Informe o nome completo ou pelo menos primeiro nome e outro "
                "sobrenome do servidor."
            ),
        )

    with session_manager.get_session() as session:
        if params.folha_servidor_id is not None:
            stmt = (
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
                .where(FolhaServidor.id == params.folha_servidor_id)
            )
            servidores = session.execute(stmt).unique().scalars().all()

            if not servidores:
                return resposta_sem_resultados(
                    mensagem=(
                        "Nao encontrei o servidor selecionado para consultar o "
                        "historico de pagamentos."
                    )
                )

            resultados = [
                serializar_servidor(servidor, params.max_meses)
                for servidor in servidores
            ]
            return HistoricoPagamentosServidorResponse(
                query=params.nome,
                total=len(resultados),
                resultados=resultados,
            ).model_dump(mode="json")

        termos = [
            t
            for t in _normalizar_texto(params.nome).split()
            if len(t) > 2  # ignora artigos: "de", "da", "do", "e"
        ]
        candidatos_stmt = (
            select(FolhaServidor.id)
            .order_by(FolhaServidor.nome.asc())
            .limit(params.limite)
        )
        for termo in termos:
            candidatos_stmt = candidatos_stmt.where(
                func.normalizar(FolhaServidor.nome).like(f"%{termo}%")
            )

        candidatos_ids = session.execute(candidatos_stmt).scalars().all()

        if not candidatos_ids:
            total_servidores_folha = session.execute(
                select(func.count(FolhaServidor.id))
            ).scalar_one()

            if total_servidores_folha == 0:
                return resposta_sem_resultados(
                    query=params.nome,
                    mensagem=(
                        "A base local de folha de pagamento esta vazia. "
                        "Importe os XMLs de folha antes de consultar salarios."
                    ),
                )

            return resposta_sem_resultados(
                query=params.nome,
                sugestao=(
                    f"Nenhum servidor encontrado com '{params.nome}'. "
                    "Confira a grafia ou tente uma combinação menos ambígua do nome, "
                    "como primeiro nome e outro sobrenome."
                ),
            )

        stmt = (
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
            .where(FolhaServidor.id.in_(candidatos_ids))
            .order_by(FolhaServidor.nome.asc())
        )
        servidores = session.execute(stmt).unique().scalars().all()

        if len(servidores) > 1:
            candidatos = [
                serializar_candidato_servidor(servidor) for servidor in servidores
            ]
            return resposta_sem_resultados(
                query=params.nome,
                total=len(candidatos),
                candidatos=candidatos,
                mensagem=(
                    "Encontrei mais de um servidor compatível com esse nome. "
                    "Escolha uma das opções pelo nome completo, cargo, "
                    "secretaria/setor ou pelo `folha_servidor_id` antes de "
                    "consultar o histórico de pagamentos."
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
