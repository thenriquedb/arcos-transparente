"""Tool publica para consultar movimentacoes diarias de estoque."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.lookup import (
    build_lookup_response,
    execute_collection_lookup_result,
)
from agents.tools.sql_tools.shared.projection import project_public_fields
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import EstoqueMovimentacao
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_movimentacoes_de_estoque_schema import (
    ConsultarMovimentacoesDeEstoqueMetadata,
    ConsultarMovimentacoesDeEstoqueParams,
    ConsultarMovimentacoesDeEstoqueResponse,
    DEFAULT_ESTOQUE_MOVEMENT_FIELDS,
    EstoqueMovimentacaoFiltroSchema,
)


def _row_to_public_dict(registro: EstoqueMovimentacao) -> dict[str, Any]:
    material = registro.estoque_material
    return {
        "origem": material.origem,
        "ano": material.exercicio,
        "material": material.material,
        "unidade_medida": material.unidade_medida,
        "data_movimento": registro.data_movimento.isoformat(),
        "tipo_movimento": registro.tipo_movimento,
        "unidade_gestora": registro.unidade_gestora,
        "almoxarifado": registro.almoxarifado,
        "localizacao": registro.localizacao,
        "classificacao": registro.classificacao,
        "quantidade": decimal_to_float(registro.quantidade),
        "valor_unitario": decimal_to_float(registro.valor_unitario),
        "valor_total": decimal_to_float(registro.valor_total),
        "custo_medio": decimal_to_float(registro.custo_medio),
    }


def load_filtered_estoque_movimentacoes(
    session,
    filtros: EstoqueMovimentacaoFiltroSchema,
) -> list[EstoqueMovimentacao]:
    registros = session.query(EstoqueMovimentacao).all()

    if filtros.origem:
        registros = [
            r
            for r in registros
            if matches_text_query(r.estoque_material.origem, filtros.origem)
        ]
    if filtros.ano:
        registros = [
            r for r in registros if r.estoque_material.exercicio == filtros.ano
        ]
    if filtros.material:
        registros = [
            r
            for r in registros
            if matches_text_query(r.estoque_material.material, filtros.material)
        ]
    if filtros.data_movimento_inicio:
        registros = [
            r for r in registros if r.data_movimento >= filtros.data_movimento_inicio
        ]
    if filtros.data_movimento_fim:
        registros = [
            r for r in registros if r.data_movimento <= filtros.data_movimento_fim
        ]
    if filtros.tipo_movimento:
        registros = [
            r
            for r in registros
            if matches_text_query(r.tipo_movimento, filtros.tipo_movimento)
        ]
    if filtros.unidade_gestora:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_gestora)
        ]
    if filtros.almoxarifado:
        registros = [
            r
            for r in registros
            if matches_text_query(r.almoxarifado, filtros.almoxarifado)
        ]
    if filtros.localizacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.localizacao, filtros.localizacao)
        ]
    if filtros.classificacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.classificacao, filtros.classificacao)
        ]

    return registros


SORT_FIELD_GETTERS = {
    "data_movimento": lambda registro: registro.data_movimento,
    "material": lambda registro: registro.estoque_material.material or "",
    "tipo_movimento": lambda registro: registro.tipo_movimento or "",
    "quantidade": lambda registro: registro.quantidade or Decimal("0"),
    "valor_total": lambda registro: registro.valor_total or Decimal("0"),
    "almoxarifado": lambda registro: registro.almoxarifado or "",
}


def project_estoque_movimentacao_fields(
    registro: EstoqueMovimentacao,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        registro,
        campos,
        serializer=_row_to_public_dict,
        default_fields=DEFAULT_ESTOQUE_MOVEMENT_FIELDS,
    )


@register(
    name="consultar_movimentacoes_de_estoque",
    scope=PUBLIC_SCOPE,
    tags=["domain:estoques", "shape:lookup", "kind:movements"],
    routing=routing_metadata(
        examples=[
            "Quais movimentacoes de estoque ocorreram em 2025?",
            "Liste as requisicoes do almoxarifado da saude.",
        ],
        hints=[
            "movimentacao de estoque",
            "requisicao",
            "almoxarifado",
            "aplicacao imediata",
            "nota fiscal de compra",
        ],
    ),
)
def consultar_movimentacoes_de_estoque(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_movimento",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista o historico diario de movimentacoes importadas do dominio de estoque.

    Use esta tool quando a pergunta pedir movimentacoes, requisicoes, notas
    fiscais de compra, aplicacoes imediatas ou outras entradas e saidas diarias
    de materiais em almoxarifado.
    NAO use para saldos sumarizados por material; para isso use
    `consultar_estoques`.
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
        schema_type=ConsultarMovimentacoesDeEstoqueParams,
        on_error=lambda exc: ConsultarMovimentacoesDeEstoqueResponse(
            total=0,
            resultados=[],
            metadata=ConsultarMovimentacoesDeEstoqueMetadata(
                ordenar_por="data_movimento",
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
        registros = load_filtered_estoque_movimentacoes(session, params.filtros)
        execution = execute_collection_lookup_result(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            empty_suggestion=(
                "Nenhuma movimentacao de estoque encontrada com os filtros."
            ),
        )

    metadata = ConsultarMovimentacoesDeEstoqueMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(DEFAULT_ESTOQUE_MOVEMENT_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarMovimentacoesDeEstoqueResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_estoque_movimentacao_fields,
        campos=params.campos,
        pagination_message_builder=lambda shown, total: (
            f"Mostrando {shown} de {total} movimentacoes de estoque encontradas."
        ),
    )
