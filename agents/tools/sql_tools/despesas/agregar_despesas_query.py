"""Tool publica para agregacoes de despesas."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import DespesaDocumento

from .agregar_despesas_schema import (
    AgregarDespesasMetadata,
    AgregarDespesasParams,
    AgregarDespesasResponse,
)
from .consultar_despesas_query import load_filtered_despesas


def _decimal_to_json(value: Decimal) -> float:
    return float(value)


def _metric(registros: list[DespesaDocumento], metrica: str) -> Decimal | int:
    if metrica == "contagem":
        return len(registros)
    field_by_metric = {
        "soma_valor_documento": "valor_documento",
        "soma_valor_empenhado": "valor_empenhado",
        "soma_valor_pago": "valor_pago",
        "soma_valor_anulado": "valor_anulado",
    }
    field = field_by_metric[metrica]
    return sum((getattr(registro, field) or Decimal(0)) for registro in registros)


def _metric_to_json(value: Decimal | int) -> float | int:
    if isinstance(value, Decimal):
        return _decimal_to_json(value)
    return value


GROUP_FIELD_GETTERS = {
    "tipo": lambda registro: registro.tipo_origem,
    "origem": lambda registro: registro.origem,
    "ano": lambda registro: registro.exercicio,
    "mes": lambda registro: registro.data_documento.month,
    "unidade_responsavel": lambda registro: registro.unidade_gestora,
    "area": lambda registro: registro.funcao,
    "credor": lambda registro: registro.credor,
    "conta_extra": lambda registro: registro.conta_extra_descricao,
}
METRIC_FIELD_GETTERS = {
    "soma_valor_documento": lambda registro: registro.valor_documento or Decimal(0),
    "soma_valor_empenhado": lambda registro: registro.valor_empenhado or Decimal(0),
    "soma_valor_pago": lambda registro: registro.valor_pago or Decimal(0),
    "soma_valor_anulado": lambda registro: registro.valor_anulado or Decimal(0),
}


def _project_despesa_group(
    group_value: Any,
    metric_value: Any,
    agrupar_por: str,
    metrica: str,
) -> dict[str, Any]:
    return {agrupar_por: group_value, metrica: metric_value}


@register(
    name=ToolName.AGREGAR_DESPESAS,
    scope=PUBLIC_SCOPE,
    tags=["domain:despesas", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quanto foi pago em despesas da saude em 2025?",
            "Quais os maiores credores da prefeitura?",
        ],
        hints=[
            "despesa",
            "total pago",
            "empenhado",
            "ranking",
            "credor",
        ],
    ),
)
def agregar_despesas(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_pago",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre documentos de despesa.

    Use esta tool quando a pergunta pedir total pago, total empenhado, total
    anulado, maiores credores ou comparacoes por area, origem, unidade ou tipo
    de documento.
    Se a pergunta usar linguagem ampla de gasto e houver interesse em ver os
    documentos que sustentam o valor, consulte primeiro `consultar_despesas` e
    use esta tool apenas como resumo complementar ou quando o usuario pedir
    explicitamente total, ranking ou comparacao.
    Quando o filtro textual for o nome de um evento, nao trate automaticamente
    a soma encontrada como "custo do evento": a descricao pode citar apenas
    despesas indiretas, preparatorias ou acessorias, como divulgacao, viagem,
    diaria, pedagio ou reuniao. Nesses casos, confirme o contexto com
    `consultar_licitacoes` e `consultar_contratos` antes de afirmar um total.
    NAO use para listar documentos individuais; para isso use
    `consultar_despesas`.
    NAO use para planejamento orcamentario; para isso use
    `agregar_planejamento`.
    NAO use para o relatorio agregado `despesas-por-funcao`; para isso use
    `agregar_despesas_por_funcao`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo`, `origem`,
            `ano`, `data_inicio`, `data_fim`, `numero`, `credor`, `cpf_cnpj`,
            `unidade_responsavel`, `area`, `conta_extra`, `contrato` e
            `descricao`. `tipo` aceita `empenho`, `restos_a_pagar`,
            `documento_extra`, `diaria` ou `passagem`. Datas em `YYYY-MM-DD`.
        agrupar_por: Campo opcional de agrupamento. Aceita `tipo`, `origem`,
            `ano`, `mes`, `unidade_responsavel`, `area`, `credor` ou
            `conta_extra`. Se nao for informado, a tool retorna um `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_documento`,
            `soma_valor_empenhado`, `soma_valor_pago` ou `soma_valor_anulado`.
        ordenar_por: Aceita `metrica` ou o mesmo valor usado em `agrupar_por`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Quantidade maxima de grupos retornados. Inteiro de 1 a 100.

    Returns:
        dict com:
        - `total_grupos`: total de grupos encontrados.
        - `resultados`: lista de grupos; cada item traz o campo de agrupamento e a
          metrica calculada.
        - `metadata`: filtros aplicados e configuracao da agregacao.
        - `valor_total`: valor agregado quando `agrupar_por` nao for informado.
        - `mensagem`: aviso quando so parte dos grupos for exibida.
        - `sugestao`: dica quando nenhuma despesa corresponder aos filtros.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "agrupar_por": agrupar_por,
            "metrica": metrica,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
        },
        schema_type=AgregarDespesasParams,
        on_error=lambda exc: AgregarDespesasResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarDespesasMetadata(
                metrica="soma_valor_pago",
                ordenar_por="metrica",
                ordem="desc",
                limite=10,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = load_filtered_despesas(session, params.filtros)

    metadata = AgregarDespesasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
    )

    execution = execute_collection_aggregate(
        registros,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica,
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        group_key_getters=GROUP_FIELD_GETTERS,
        metric_getters=METRIC_FIELD_GETTERS,
        serialize_metric=_metric_to_json,
    )
    suggestion = (
        "Nenhuma despesa encontrada com os filtros."
        if (
            (params.agrupar_por is None and execution.source_count == 0)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarDespesasResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            source_count=execution.source_count,
            suggestion=suggestion,
        ),
        project_group=(_project_despesa_group if params.agrupar_por is not None else None),
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
