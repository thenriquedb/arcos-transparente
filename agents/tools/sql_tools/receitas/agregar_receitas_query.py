"""Tool publica para agregacoes de receitas."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.aggregate import (
    AggregateExecutionResult,
    build_aggregate_response,
    execute_collection_aggregate,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager

from .agregar_receitas_schema import (
    AgregacaoReceitasItem,
    AgregarReceitasMetadata,
    AgregarReceitasParams,
    AgregarReceitasResponse,
)
from .shared.querying import (
    GROUP_FIELD_GETTERS,
    load_filtered_receitas,
    METRIC_FIELD_GETTERS,
)


@register(
    name="agregar_receitas",
    scope=PUBLIC_SCOPE,
    tags=["domain:receitas", "shape:aggregate"],
    routing=routing_metadata(
        examples=[
            "Quanto foi arrecadado com IPTU em 2025?",
            "Qual tributo mais arrecadou?",
        ],
        hints=[
            "receita",
            "arrecadado",
            "lancado",
            "ranking",
            "tributo",
        ],
    ),
)
def agregar_receitas(
    filtros: dict[str, Any] | None = None,
    agrupar_por: str | None = None,
    metrica: str = "soma_valor_recebido",
    ordenar_por: str = "metrica",
    ordem: str = "desc",
    limite: int = 10,
) -> dict[str, Any]:
    """
    Calcula totais, contagens e rankings sobre receitas.

    Use esta tool quando a pergunta pedir quanto foi arrecadado, quanto foi
    lancado ou qual categoria, tributo ou unidade responsavel mais arrecadou.
    NAO use para listar registros individuais; para isso use `consultar_receitas`.
    NAO use para planejamento orcamentario ou despesas; para isso use
    `agregar_planejamento` ou `agregar_despesas`.

    O padrao usa arrecadacao efetiva. Para valores apenas lancados, informe
    `tipo_de_dado='lancamento'`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo_de_dado`,
            `ano`, `mes`, `mes_inicio`, `mes_fim`, `unidade_responsavel`,
            `categoria`, `categoria_codigo`, `tipo`, `tributo`,
            `origem_do_recurso`, `tema`, `valor_min` e `valor_max`. `mes`,
            `mes_inicio` e `mes_fim` aceitam numero de 1 a 12 ou nome do mes.
        agrupar_por: Campo opcional de agrupamento. Aceita `mes`,
            `unidade_responsavel`, `categoria`, `tipo`, `tributo` ou
            `origem_do_recurso`. Se nao for informado, a tool retorna um
            `valor_total`.
        metrica: Metrica calculada. Aceita `contagem`, `soma_valor_previsto`,
            `soma_valor_recebido`, `soma_valor_lancado`,
            `soma_valor_em_divida_ativa` ou
            `soma_valor_em_cobranca_judicial`.
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
        - `sugestao`: dica quando nenhum registro corresponder aos filtros.
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
        schema_type=AgregarReceitasParams,
        on_error=lambda exc: AgregarReceitasResponse(
            total_grupos=0,
            resultados=[],
            metadata=AgregarReceitasMetadata(
                metrica="soma_valor_recebido",
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
        registros = load_filtered_receitas(session, params.filtros)

    metadata = AgregarReceitasMetadata(
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
        serialize_metric=lambda value: value,
    )
    suggestion = (
        "Nenhum registro de receitas encontrado com os filtros."
        if (
            (params.agrupar_por is None and not execution.valor_total)
            or (params.agrupar_por is not None and not execution.rows)
        )
        else None
    )
    return build_aggregate_response(
        response_type=AgregarReceitasResponse,
        metadata=metadata,
        execution=AggregateExecutionResult(
            total_grupos=execution.total_grupos,
            rows=execution.rows,
            valor_total=execution.valor_total,
            suggestion=suggestion,
        ),
        item_model=AgregacaoReceitasItem if params.agrupar_por is not None else None,
        agrupar_por=params.agrupar_por,
        metrica=params.metrica if params.agrupar_por is not None else None,
    )
