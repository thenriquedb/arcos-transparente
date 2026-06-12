"""Tool para buscar historico de pagamentos de um servidor."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager
from database.models import Eleito, FolhaPagamentoRegistro, FolhaServidor
from database.session import _normalizar_texto
from shared.utils.text import matches_text_query, normalize_search_text

from .shared.params import BuscarHistoricoPagamentosServidorParams
from .shared.responses import HistoricoPagamentosServidorResponse
from .shared.runtime import (
    resposta_sem_resultados,
    serializar_candidato_servidor,
    serializar_servidor,
)


_CARGO_POLITICO_ALIASES = {
    "prefeito": "prefeito",
    "prefeita": "prefeito",
    "vice": "vice-prefeito",
    "vice prefeito": "vice-prefeito",
    "vice-prefeito": "vice-prefeito",
    "viceprefeito": "vice-prefeito",
    "vice prefeita": "vice-prefeito",
    "vice-prefeita": "vice-prefeito",
    "viceprefeita": "vice-prefeito",
    "vereador": "vereador",
    "vereadora": "vereador",
}


@register(
    name=ToolName.BUSCAR_HISTORICO_DE_PAGAMENTOS_DO_SERVIDOR,
    scope=PUBLIC_SCOPE,
    tags=["domain:folha", "shape:history"],
    routing=routing_metadata(
        examples=[
            "Qual o salario de Ronaldo Ribeiro?",
            "Quanto o prefeito recebe?",
        ],
        hints=[
            "salario individual",
            "quanto recebe",
            "historico de pagamentos",
            "nome de pessoa",
            "folha",
        ],
    ),
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
    Esta tool tambem aceita `nome="prefeito"`, `nome="vice"` ou
    `nome="vereador"` como atalho: nesses casos, resolve automaticamente o
    nome completo na base de eleitos antes de consultar a folha.
    Se a pergunta mencionar apenas cargo politico, como "prefeito", "vice" ou
    "vereador", primeiro use `consultar_eleitos` para descobrir o
    `nome_completo` em exercicio e em seguida chame esta tool com esse nome.
    Se preferir, tambem pode usar o atalho automatico com `nome="prefeito"`,
    `nome="vice"` ou `nome="vereador"` e a tool fara essa resolucao sozinha.
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
            mensagem=("Informe um nome de servidor ou selecione um `folha_servidor_id` para realizar a busca."),
        )

    with session_manager.get_session() as session:
        if params.folha_servidor_id is not None:
            return _responder_por_folha_servidor_id(session, params)

        nome_resolvido = params.nome or ""
        cargo_politico = _resolve_cargo_politico_alias(nome_resolvido)
        if cargo_politico is not None:
            nome_resolvido, mensagem_erro = _resolve_nome_por_cargo_politico(
                session,
                cargo_politico,
            )
            if mensagem_erro is not None:
                return resposta_sem_resultados(
                    query=params.nome,
                    mensagem=mensagem_erro,
                )

        if len(nome_resolvido.split()) < 2:
            return resposta_sem_resultados(
                query=params.nome,
                mensagem=(
                    "Informação insuficiente para consultar salário individual. "
                    "Informe o nome completo ou pelo menos primeiro nome e outro "
                    "sobrenome do servidor."
                ),
            )

        grupos = _buscar_grupos_por_nome(session, nome_resolvido)

        if not grupos:
            return _resposta_para_busca_vazia(
                session,
                params,
                cargo_politico=cargo_politico,
                nome_resolvido=nome_resolvido,
            )

        grupos_limitados = list(grupos.values())[: params.limite]

        if len(grupos) > 1:
            candidatos = [serializar_candidato_servidor(grupo) for grupo in grupos_limitados]
            return resposta_sem_resultados(
                query=params.nome,
                total=len(grupos),
                candidatos=candidatos,
                mensagem=(
                    "Encontrei mais de um servidor compatível com esse nome. "
                    "Escolha uma das opções pelo nome completo, cargo, "
                    "secretaria/setor ou pelo `folha_servidor_id` antes de "
                    "consultar o histórico de pagamentos."
                ),
            )

        servidores = grupos_limitados[0]

    resultados = [serializar_servidor(servidores, params.max_meses)]

    return HistoricoPagamentosServidorResponse(
        query=params.nome,
        total=len(resultados),
        resultados=resultados,
    ).model_dump(mode="json")


def _responder_por_folha_servidor_id(
    session,
    params: BuscarHistoricoPagamentosServidorParams,
) -> dict[str, Any]:
    """Responde a selecao direta de um candidato por `folha_servidor_id`."""

    representante = (
        session.execute(_base_folha_servidores_stmt().where(FolhaServidor.id == params.folha_servidor_id))
        .unique()
        .scalars()
        .one_or_none()
    )

    if representante is None:
        return resposta_sem_resultados(
            mensagem=("Nao encontrei o servidor selecionado para consultar o historico de pagamentos.")
        )

    servidores = _carregar_servidores_por_nome(session, representante.nome)
    resultados = [serializar_servidor(servidores, params.max_meses)]
    return HistoricoPagamentosServidorResponse(
        query=params.nome,
        total=len(resultados),
        resultados=resultados,
    ).model_dump(mode="json")


def _buscar_grupos_por_nome(
    session,
    nome_resolvido: str,
) -> dict[str, list[FolhaServidor]]:
    """Busca servidores cujo nome contem todos os termos relevantes do nome."""

    termos = [
        t
        for t in _normalizar_texto(nome_resolvido).split()
        if len(t) > 2  # ignora artigos: "de", "da", "do", "e"
    ]
    candidatos_stmt = _base_folha_servidores_stmt().order_by(
        FolhaServidor.nome.asc(),
        FolhaServidor.competencia_referencia.desc(),
        FolhaServidor.id.desc(),
    )
    for termo in termos:
        candidatos_stmt = candidatos_stmt.where(func.normalizar(FolhaServidor.nome).like(f"%{termo}%"))

    candidatos = session.execute(candidatos_stmt).unique().scalars().all()
    return _agrupar_servidores_por_nome(candidatos)


def _resposta_para_busca_vazia(
    session,
    params: BuscarHistoricoPagamentosServidorParams,
    *,
    cargo_politico: str | None,
    nome_resolvido: str,
) -> dict[str, Any]:
    """Explica a ausencia de resultados distinguindo base vazia de nome ausente."""

    total_servidores_folha = session.execute(select(func.count(FolhaServidor.id))).scalar_one()

    if total_servidores_folha == 0:
        return resposta_sem_resultados(
            query=params.nome,
            mensagem=(
                "A base local de folha de pagamento esta vazia. Importe os XMLs de folha antes de consultar salarios."
            ),
        )

    if cargo_politico is not None:
        return resposta_sem_resultados(
            query=params.nome,
            mensagem=(
                f"Identifiquei o {cargo_politico} em exercício como "
                f"'{nome_resolvido}', mas não encontrei esse nome na base "
                "local de folha de pagamento."
            ),
        )

    return resposta_sem_resultados(
        query=params.nome,
        sugestao=(
            f"Nenhum servidor encontrado com '{nome_resolvido}'. "
            "Confira a grafia ou tente uma combinação menos ambígua do nome, "
            "como primeiro nome e outro sobrenome."
        ),
    )


def _resolve_cargo_politico_alias(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_search_text(value).strip()
    normalized = re.sub(r"^(?:o|a|do|da|de)\s+", "", normalized).strip()
    if resolved := _CARGO_POLITICO_ALIASES.get(normalized):
        return resolved

    for alias, resolved in sorted(
        _CARGO_POLITICO_ALIASES.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if normalized.startswith(f"{alias} "):
            return resolved

    return None


def _resolve_nome_por_cargo_politico(
    session,
    cargo_politico: str,
) -> tuple[str, str | None]:
    eleitos = (
        session.execute(
            select(Eleito)
            .where(Eleito.tipo_politico == cargo_politico)
            .order_by(Eleito.mandato_inicio.desc(), Eleito.nome_completo.asc())
        )
        .scalars()
        .all()
    )
    em_exercicio = [eleito for eleito in eleitos if matches_text_query(eleito.mandato_status, "em exercicio")]

    if not em_exercicio:
        return (
            "",
            f"Não encontrei o {cargo_politico} em exercício nos dados disponíveis da base local até o momento.",
        )

    if len(em_exercicio) > 1:
        nomes = ", ".join(eleito.nome_completo for eleito in em_exercicio[:5])
        return (
            "",
            f"Encontrei mais de um {cargo_politico} em exercício: {nomes}. Informe o nome para consultar o salário individual.",
        )

    return em_exercicio[0].nome_completo, None


def _base_folha_servidores_stmt():
    return select(FolhaServidor).options(
        joinedload(FolhaServidor.pagamentos).joinedload(FolhaPagamentoRegistro.cargo),
        joinedload(FolhaServidor.pagamentos).joinedload(FolhaPagamentoRegistro.lotacao),
    )


def _carregar_servidores_por_nome(session, nome: str) -> list[FolhaServidor]:
    return (
        session.execute(
            _base_folha_servidores_stmt()
            .where(FolhaServidor.nome == nome)
            .order_by(
                FolhaServidor.competencia_referencia.desc(),
                FolhaServidor.id.desc(),
            )
        )
        .unique()
        .scalars()
        .all()
    )


def _agrupar_servidores_por_nome(
    servidores: list[FolhaServidor],
) -> dict[str, list[FolhaServidor]]:
    grupos: dict[str, list[FolhaServidor]] = {}
    for servidor in servidores:
        grupos.setdefault(servidor.nome, []).append(servidor)
    return grupos
