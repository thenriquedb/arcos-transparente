"""Tool publica para consultas amplas de receitas."""

from __future__ import annotations

from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager

from .consultar_receitas_schema import (
    ConsultarReceitasMetadata,
    ConsultarReceitasParams,
    ConsultarReceitasResponse,
)
from .shared.filters import ALLOWED_RECEITA_FIELDS
from .shared.querying import SORT_FIELD_GETTERS, load_filtered_receitas
from .shared.runtime import project_receita_fields


@register(
    name="consultar_receitas",
    scope=PUBLIC_SCOPE,
    tags=["domain:receitas", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste receitas do FUNDEB em 2025.",
            "Quais receitas foram arrecadadas em abril?",
        ],
        hints=[
            "receita",
            "arrecadacao",
            "lancamento",
            "tributo",
            "lista",
        ],
    ),
)
def consultar_receitas(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista receitas por categoria, tributo, unidade responsavel, mes e valor.

    Use esta tool quando a pergunta pedir quais receitas foram arrecadadas ou
    lancadas, ou quando precisar listar registros individuais de arrecadacao.
    NAO use para totais, comparacoes ou rankings agregados; para isso use
    `agregar_receitas`.
    NAO use para planejamento orcamentario ou despesas; para isso use
    `consultar_planejamento` ou `consultar_despesas`.

    Use `tipo_de_dado='arrecadacao'` para valores efetivamente recebidos.
    Use `tipo_de_dado='lancamento'` para valores apenas lancados.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `tipo_de_dado`,
            `ano`, `mes`, `mes_inicio`, `mes_fim`, `unidade_responsavel`,
            `categoria`, `categoria_codigo`, `tipo`, `tributo`,
            `origem_do_recurso`, `tema`, `valor_min` e `valor_max`. `mes`,
            `mes_inicio` e `mes_fim` aceitam numero de 1 a 12 ou nome do mes.
        ordenar_por: Campo de ordenacao. Aceita `ano`, `mes_num`, `data`,
            `unidade_responsavel`, `categoria`, `tipo`, `tributo`,
            `valor_previsto`, `valor_recebido`, `valor_lancado`,
            `valor_em_divida_ativa` ou `valor_em_cobranca_judicial`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos de
            receita retornados em cada item.

    Returns:
        dict com:
        - `total`: total de registros encontrados antes da paginacao.
        - `resultados`: lista de receitas; cada item pode incluir `id`,
          `tipo_de_dado`, `ano`, `mes`, `mes_num`, `data`,
          `unidade_responsavel`, `categoria_codigo`, `categoria`, `tipo`,
          `tributo`, `origem_do_recurso`, `valor_previsto`, `valor_recebido`,
          `valor_previsto_bruto`, `valor_recebido_bruto`,
          `descontos_previstos`, `descontos_realizados`, `valor_lancado`,
          `valor_em_divida_ativa` e `valor_em_cobranca_judicial`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum registro for encontrado.
    """
    validated = validate_tool_params(
        {
            "filtros": filtros,
            "ordenar_por": ordenar_por,
            "ordem": ordem,
            "limite": limite,
            "offset": offset,
            "campos": campos,
        },
        schema_type=ConsultarReceitasParams,
        on_error=lambda exc: ConsultarReceitasResponse(
            total=0,
            resultados=[],
            metadata=ConsultarReceitasMetadata(
                ordenar_por="data",
                ordem="desc",
                limite=10,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        registros = load_filtered_receitas(session, params.filtros)
        total, pagina = execute_collection_lookup(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            tie_breaker_getters=(lambda row: row.get("id") or 0,),
        )

    metadata = ConsultarReceitasMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_RECEITA_FIELDS),
    )

    tipo_label = "arrecadacoes" if params.filtros.tipo_de_dado == "arrecadacao" else "lancamentos"
    execution = LookupExecutionResult(
        total=total,
        rows=pagina,
        suggestion=(f"Nenhum registro de {tipo_label} encontrado com os filtros." if not pagina else None),
    )
    return build_lookup_response(
        response_type=ConsultarReceitasResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_receita_fields,
        campos=params.campos,
    )
