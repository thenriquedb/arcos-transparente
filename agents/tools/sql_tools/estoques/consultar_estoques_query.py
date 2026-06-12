"""Tool publica para consultas de saldo de estoque."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.filtering import (
    apply_declared_filters,
    equals_filter,
    max_filter,
    min_filter,
    predicate_filter,
    text_filter,
)
from agents.tools.sql_tools.shared.lookup import (
    build_lookup_response,
    execute_collection_lookup_result,
)
from agents.tools.sql_tools.shared.projection import project_public_fields
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EstoqueMaterial
from shared.utils.decimal_to_float import decimal_to_float

from .consultar_estoques_schema import (
    DEFAULT_ESTOQUES_FIELDS,
    ConsultarEstoquesMetadata,
    ConsultarEstoquesParams,
    ConsultarEstoquesResponse,
    EstoqueFiltroSchema,
)


def _row_to_public_dict(registro: EstoqueMaterial) -> dict[str, Any]:
    return {
        "origem": registro.origem,
        "ano": registro.exercicio,
        "material": registro.material,
        "unidade_medida": registro.unidade_medida,
        "periodo_inicio": registro.periodo_inicio.isoformat(),
        "periodo_fim": registro.periodo_fim.isoformat(),
        "saldo_anterior_quantidade": decimal_to_float(registro.saldo_anterior_quantidade),
        "saldo_anterior_valor": decimal_to_float(registro.saldo_anterior_valor),
        "entrada_quantidade": decimal_to_float(registro.entrada_quantidade),
        "entrada_valor": decimal_to_float(registro.entrada_valor),
        "saida_quantidade": decimal_to_float(registro.saida_quantidade),
        "saida_valor": decimal_to_float(registro.saida_valor),
        "saldo_quantidade": decimal_to_float(registro.saldo_quantidade),
        "saldo_valor": decimal_to_float(registro.saldo_valor),
    }


_ESTOQUES_FILTER_CONDITIONS = (
    text_filter("origem", lambda r: r.origem),
    equals_filter("ano", lambda r: r.exercicio),
    text_filter("material", lambda r: r.material),
    text_filter("unidade_medida", lambda r: r.unidade_medida),
    predicate_filter("periodo_inicio", lambda r, v: r.periodo_fim >= v),
    predicate_filter("periodo_fim", lambda r, v: r.periodo_inicio <= v),
    min_filter("entrada_valor_min", lambda r: r.entrada_valor),
    max_filter("entrada_valor_max", lambda r: r.entrada_valor),
    min_filter("saida_valor_min", lambda r: r.saida_valor),
    max_filter("saida_valor_max", lambda r: r.saida_valor),
    min_filter("saldo_quantidade_min", lambda r: r.saldo_quantidade),
    max_filter("saldo_quantidade_max", lambda r: r.saldo_quantidade),
    min_filter("saldo_valor_min", lambda r: r.saldo_valor),
    max_filter("saldo_valor_max", lambda r: r.saldo_valor),
)


def load_filtered_estoques(
    session,
    filtros: EstoqueFiltroSchema,
) -> list[EstoqueMaterial]:
    """Carrega saldos de estoque aplicando os filtros públicos declarados."""

    registros = list(session.execute(select(EstoqueMaterial)).scalars())
    return apply_declared_filters(registros, filtros, _ESTOQUES_FILTER_CONDITIONS)


SORT_FIELD_GETTERS = {
    "periodo_fim": lambda registro: registro.periodo_fim,
    "material": lambda registro: registro.material or "",
    "entrada_valor": lambda registro: registro.entrada_valor or Decimal(0),
    "saida_valor": lambda registro: registro.saida_valor or Decimal(0),
    "saldo_quantidade": lambda registro: registro.saldo_quantidade or Decimal(0),
    "saldo_valor": lambda registro: registro.saldo_valor or Decimal(0),
}


def project_estoque_fields(
    registro: EstoqueMaterial,
    campos: list[str],
) -> dict[str, Any]:
    """Projeta o registro nos campos publicos solicitados."""

    return project_public_fields(
        registro,
        campos,
        serializer=_row_to_public_dict,
        default_fields=DEFAULT_ESTOQUES_FIELDS,
    )


@register(
    name=ToolName.CONSULTAR_ESTOQUES,
    scope=PUBLIC_SCOPE,
    tags=["domain:estoques", "shape:lookup", "kind:summary"],
    routing=routing_metadata(
        examples=[
            "Quais materiais estao em estoque em 2025?",
            "Liste o saldo de materiais do almoxarifado da prefeitura.",
        ],
        hints=[
            "estoque",
            "saldo",
            "material",
            "almoxarifado",
            "estoques",
        ],
    ),
)
def consultar_estoques(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "periodo_fim",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista saldos sumarizados de materiais importados do dominio de estoque.

    Use esta tool quando a pergunta pedir quais materiais estao em estoque,
    qual o saldo de um material, quais itens tiveram entrada ou saida em um
    periodo, ou quando for preciso mostrar a base detalhada que sustenta um
    ranking ou total de saldo.
    NAO use para somas, contagens ou rankings agregados; para isso use
    `agregar_estoques`.
    NAO use para historico diario de requisicoes, compras ou aplicacoes
    imediatas; para isso use `consultar_movimentacoes_de_estoque`.
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
        schema_type=ConsultarEstoquesParams,
        on_error=lambda exc: ConsultarEstoquesResponse(
            total=0,
            resultados=[],
            metadata=ConsultarEstoquesMetadata(
                ordenar_por="periodo_fim",
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
        registros = load_filtered_estoques(session, params.filtros)
        execution = execute_collection_lookup_result(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            empty_suggestion="Nenhum material de estoque encontrado com os filtros.",
        )

    metadata = ConsultarEstoquesMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(DEFAULT_ESTOQUES_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarEstoquesResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_estoque_fields,
        campos=params.campos,
        pagination_message_builder=lambda shown, total: (
            f"Mostrando {shown} de {total} materiais de estoque encontrados."
        ),
    )
