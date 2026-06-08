"""Tool publica para consultas de saldo de estoque."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    LookupExecutionResult,
    build_lookup_response,
    execute_collection_lookup,
)
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EstoqueMaterial
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_estoques_schema import (
    ConsultarEstoquesMetadata,
    ConsultarEstoquesParams,
    ConsultarEstoquesResponse,
    DEFAULT_ESTOQUES_FIELDS,
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
        "saldo_anterior_quantidade": decimal_to_float(
            registro.saldo_anterior_quantidade
        ),
        "saldo_anterior_valor": decimal_to_float(registro.saldo_anterior_valor),
        "entrada_quantidade": decimal_to_float(registro.entrada_quantidade),
        "entrada_valor": decimal_to_float(registro.entrada_valor),
        "saida_quantidade": decimal_to_float(registro.saida_quantidade),
        "saida_valor": decimal_to_float(registro.saida_valor),
        "saldo_quantidade": decimal_to_float(registro.saldo_quantidade),
        "saldo_valor": decimal_to_float(registro.saldo_valor),
    }


def load_filtered_estoques(
    session,
    filtros: EstoqueFiltroSchema,
) -> list[EstoqueMaterial]:
    registros = session.query(EstoqueMaterial).all()

    if filtros.origem:
        registros = [
            r for r in registros if matches_text_query(r.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [r for r in registros if r.exercicio == filtros.ano]
    if filtros.material:
        registros = [
            r for r in registros if matches_text_query(r.material, filtros.material)
        ]
    if filtros.unidade_medida:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_medida, filtros.unidade_medida)
        ]
    if filtros.periodo_inicio:
        registros = [r for r in registros if r.periodo_fim >= filtros.periodo_inicio]
    if filtros.periodo_fim:
        registros = [r for r in registros if r.periodo_inicio <= filtros.periodo_fim]
    if filtros.entrada_valor_min is not None:
        registros = [
            r
            for r in registros
            if (r.entrada_valor or Decimal("0")) >= filtros.entrada_valor_min
        ]
    if filtros.entrada_valor_max is not None:
        registros = [
            r
            for r in registros
            if (r.entrada_valor or Decimal("0")) <= filtros.entrada_valor_max
        ]
    if filtros.saida_valor_min is not None:
        registros = [
            r
            for r in registros
            if (r.saida_valor or Decimal("0")) >= filtros.saida_valor_min
        ]
    if filtros.saida_valor_max is not None:
        registros = [
            r
            for r in registros
            if (r.saida_valor or Decimal("0")) <= filtros.saida_valor_max
        ]
    if filtros.saldo_quantidade_min is not None:
        registros = [
            r
            for r in registros
            if (r.saldo_quantidade or Decimal("0")) >= filtros.saldo_quantidade_min
        ]
    if filtros.saldo_quantidade_max is not None:
        registros = [
            r
            for r in registros
            if (r.saldo_quantidade or Decimal("0")) <= filtros.saldo_quantidade_max
        ]
    if filtros.saldo_valor_min is not None:
        registros = [
            r
            for r in registros
            if (r.saldo_valor or Decimal("0")) >= filtros.saldo_valor_min
        ]
    if filtros.saldo_valor_max is not None:
        registros = [
            r
            for r in registros
            if (r.saldo_valor or Decimal("0")) <= filtros.saldo_valor_max
        ]

    return registros


SORT_FIELD_GETTERS = {
    "periodo_fim": lambda registro: registro.periodo_fim,
    "material": lambda registro: registro.material or "",
    "entrada_valor": lambda registro: registro.entrada_valor or Decimal("0"),
    "saida_valor": lambda registro: registro.saida_valor or Decimal("0"),
    "saldo_quantidade": lambda registro: registro.saldo_quantidade or Decimal("0"),
    "saldo_valor": lambda registro: registro.saldo_valor or Decimal("0"),
}


def project_estoque_fields(
    registro: EstoqueMaterial,
    campos: list[str],
) -> dict[str, Any]:
    selected = campos or list(DEFAULT_ESTOQUES_FIELDS)
    return {
        campo: value
        for campo, value in _row_to_public_dict(registro).items()
        if campo in selected
    }


@register(
    name="consultar_estoques",
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
        total, pagina = execute_collection_lookup(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
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
        execution=LookupExecutionResult(
            total=total,
            rows=pagina,
            suggestion=(
                "Nenhum material de estoque encontrado com os filtros."
                if not pagina
                else None
            ),
        ),
        project_row=project_estoque_fields,
        campos=params.campos,
        pagination_message_builder=lambda shown, total: (
            f"Mostrando {shown} de {total} materiais de estoque encontrados."
        ),
    )
