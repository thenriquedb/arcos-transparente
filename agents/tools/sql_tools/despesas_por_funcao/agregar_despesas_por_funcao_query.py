"""Tool publica para agregacoes do relatorio `despesas-por-funcao`."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from database import session as session_manager
from database.models import DespesaPorFuncao

from .agregar_despesas_por_funcao_schema import (
    AgregarDespesasPorFuncaoMetadata,
    AgregarDespesasPorFuncaoParams,
    AgregarDespesasPorFuncaoResponse,
)
from .consultar_despesas_por_funcao_query import load_filtered_despesas_por_funcao


def _metric(registros: list[DespesaPorFuncao], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field_by_metric = {
        "soma_dotacao_inicial": "dotacao_inicial",
        "soma_creditos_adicionais": "creditos_adicionais",
        "soma_dotacao_atualizada": "dotacao_atualizada",
        "soma_valor_empenhado": "valor_empenhado",
        "soma_valor_em_liquidacao": "valor_em_liquidacao",
        "soma_valor_liquidado": "valor_liquidado",
        "soma_valor_pago": "valor_pago",
    }
    field = field_by_metric[metrica]
    return sum((getattr(registro, field) or Decimal("0")) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _group_value(registro: DespesaPorFuncao, group: str) -> str | int | None:
    mapping = {
        "origem": registro.origem,
        "ano": registro.exercicio,
        "unidade_gestora": registro.unidade_gestora,
        "funcao": registro.funcao,
    }
    return mapping[group]


@register(
    name="agregar_despesas_por_funcao",
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas_por_funcao", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Qual foi o total pago no relatorio de despesas por funcao em 2025?",
            "Quais funcoes tiveram maior valor pago no relatorio de despesas por funcao?",
        ],
        hints=[
            "despesas por funcao",
            "ranking por funcao",
            "dotacao atualizada",
            "creditos adicionais",
            "valor pago",
        ],
    ),
)
def agregar_despesas_por_funcao(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, comparacoes e rankings sobre o relatorio `despesas-por-funcao`.

    Use esta tool quando a pergunta pedir total, comparacao, contagem ou ranking
    sobre as linhas agregadas do relatorio `despesas-por-funcao`.
    NAO use para perguntas amplas como "qual foi o gasto com saude em 2025?"
    quando o usuario nao pediu explicitamente apenas um total. Nesses casos,
    use `consultar_despesas_por_funcao` e mostre os estagios
    `valor_empenhado`, `valor_em_liquidacao`, `valor_liquidado` e `valor_pago`.
    Se o usuario ja informar um ano, como "em 2025", esse recorte ja basta;
    nao peca dia e mes para responder.
    NAO use para listar linhas individuais do relatorio; para isso use
    `consultar_despesas_por_funcao`.
    NAO use para planejamento mensal por programa ou acao; para isso use
    `agregar_planejamento`.
    NAO use para somar documentos de despesa efetivamente emitidos; para isso use
    `agregar_despesas`.
    """
    try:
        params = AgregarDespesasPorFuncaoParams.model_validate(
            {
                "filtros": filtros,
                "agrupar_por": agrupar_por,
                "metrica": metrica,
                "ordenar_por": ordenar_por,
                "ordem": ordem,
                "limite": limite,
            }
        )
    except ValidationError as exc:
        fallback_metadata = AgregarDespesasPorFuncaoMetadata(
            metrica="soma_valor_pago",
            ordenar_por="metrica",
            ordem="desc",
            limite=10,
        )
        return AgregarDespesasPorFuncaoResponse(
            total_grupos=0,
            resultados=[],
            metadata=fallback_metadata,
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json")

    with session_manager.get_session() as session:
        registros = load_filtered_despesas_por_funcao(session, params.filtros)

    metadata = AgregarDespesasPorFuncaoMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    if params.agrupar_por is None:
        valor_total = _metric_to_json(_metric(registros, params.metrica))
        return AgregarDespesasPorFuncaoResponse(
            total_grupos=0,
            resultados=[],
            metadata=metadata,
            valor_total=valor_total,
            sugestao=(
                "Nenhum registro de despesas por funcao encontrado com os filtros."
                if not valor_total
                else None
            ),
        ).model_dump(mode="json")

    grupos: dict[str, list[DespesaPorFuncao]] = {}
    for registro in registros:
        valor = _group_value(registro, params.agrupar_por) or "nao_informado"
        grupos.setdefault(str(valor), []).append(registro)

    resultados = []
    for group_value, group_rows in grupos.items():
        resultados.append(
            {
                params.agrupar_por: group_value,
                params.metrica: _metric_to_json(_metric(group_rows, params.metrica)),
            }
        )

    reverse = params.ordem == "desc"
    if params.ordenar_por == "metrica":
        resultados.sort(key=lambda item: item[params.metrica], reverse=reverse)
    else:
        resultados.sort(key=lambda item: item[params.agrupar_por], reverse=reverse)

    total_grupos = len(resultados)
    resultados = resultados[: params.limite]
    mensagem = None
    if total_grupos > len(resultados):
        mensagem = f"Mostrando {len(resultados)} de {total_grupos} grupos encontrados."

    return AgregarDespesasPorFuncaoResponse(
        total_grupos=total_grupos,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(
            "Nenhum registro de despesas por funcao encontrado com os filtros."
            if not resultados
            else None
        ),
    ).model_dump(mode="json")
