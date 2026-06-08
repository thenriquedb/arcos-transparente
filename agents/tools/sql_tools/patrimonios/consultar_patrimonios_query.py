"""Tool publica para consultas amplas de patrimonio."""

from __future__ import annotations

from datetime import date
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
from database.models import Patrimonio
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from .consultar_patrimonios_schema import (
    ALLOWED_PATRIMONIO_FIELDS,
    ConsultarPatrimoniosMetadata,
    ConsultarPatrimoniosParams,
    ConsultarPatrimoniosResponse,
    PatrimonioFiltroSchema,
)


def _row_to_public_dict(registro: Patrimonio) -> dict[str, Any]:
    return {
        "unidade_responsavel": registro.unidade_gestora,
        "placa": registro.placa,
        "descricao": registro.descricao_item,
        "classificacao": registro.classificacao,
        "localizacao": registro.localizacao,
        "status": registro.status,
        "situacao": registro.situacao_bem,
        "tipo_ingresso": registro.tipo_ingresso,
        "data_aquisicao": registro.data_aquisicao.isoformat()
        if registro.data_aquisicao
        else None,
        "data_baixa": registro.data_baixa.isoformat() if registro.data_baixa else None,
        "valor_ingresso": decimal_to_float(registro.valor_ingresso),
        "valor_atualizado": decimal_to_float(registro.valor_atualizado),
    }


def load_filtered_patrimonios(
    session, filtros: PatrimonioFiltroSchema
) -> list[Patrimonio]:
    registros = session.query(Patrimonio).all()

    if filtros.unidade_responsavel:
        registros = [
            r
            for r in registros
            if matches_text_query(r.unidade_gestora, filtros.unidade_responsavel)
        ]
    if filtros.placa:
        registros = [r for r in registros if matches_text_query(r.placa, filtros.placa)]
    if filtros.descricao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.descricao_item, filtros.descricao)
        ]
    if filtros.classificacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.classificacao, filtros.classificacao)
        ]
    if filtros.localizacao:
        registros = [
            r
            for r in registros
            if matches_text_query(r.localizacao, filtros.localizacao)
        ]
    if filtros.status:
        registros = [
            r for r in registros if matches_text_query(r.status, filtros.status)
        ]
    if filtros.situacao:
        registros = [
            r for r in registros if matches_text_query(r.situacao_bem, filtros.situacao)
        ]
    if filtros.tipo_ingresso:
        registros = [
            r
            for r in registros
            if matches_text_query(r.tipo_ingresso, filtros.tipo_ingresso)
        ]
    if filtros.data_aquisicao_inicio:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao >= filtros.data_aquisicao_inicio
        ]
    if filtros.data_aquisicao_fim:
        registros = [
            r
            for r in registros
            if r.data_aquisicao is not None
            and r.data_aquisicao <= filtros.data_aquisicao_fim
        ]

    return registros


SORT_FIELD_GETTERS = {
    "data_aquisicao": lambda registro: registro.data_aquisicao or date.min,
    "valor_atualizado": lambda registro: registro.valor_atualizado or Decimal("0"),
    "valor_ingresso": lambda registro: registro.valor_ingresso or Decimal("0"),
    "descricao": lambda registro: registro.descricao_item or "",
    "localizacao": lambda registro: registro.localizacao or "",
    "placa": lambda registro: registro.placa or "",
}


def project_patrimonio_fields(
    registro: Patrimonio,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        registro,
        campos,
        serializer=_row_to_public_dict,
        default_fields=ALLOWED_PATRIMONIO_FIELDS,
    )


@register(
    name="consultar_patrimonios",
    scope=PUBLIC_SCOPE,
    tags=["domain:patrimonios", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Liste os patrimonios da educacao em 2025.",
            "Quais bens estao na prefeitura?",
        ],
        hints=[
            "patrimonio",
            "bem",
            "localizacao",
            "aquisicao",
            "lista",
        ],
    ),
)
def consultar_patrimonios(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_aquisicao",
    ordem: str = "desc",
    limite: int = 10,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista bens patrimoniais por placa, descricao, localizacao, status e valor.

    Use esta tool quando a pergunta pedir quais bens existem, onde estao, qual a
    classificacao de um bem ou quais itens foram adquiridos em certo periodo.
    NAO use para totais, somas ou rankings agregados; para isso use
    `agregar_patrimonios`.
    NAO use para contratos ou licitacoes de aquisicao; para isso use
    `consultar_contratos` ou `consultar_licitacoes`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos:
            `unidade_responsavel`, `placa`, `descricao`, `classificacao`,
            `localizacao`, `status`, `situacao`, `tipo_ingresso`,
            `data_aquisicao_inicio` e `data_aquisicao_fim`. Datas em
            `YYYY-MM-DD`.
        ordenar_por: Campo de ordenacao. Aceita `data_aquisicao`,
            `valor_atualizado`, `valor_ingresso`, `descricao`, `localizacao`
            ou `placa`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com qualquer subconjunto dos campos publicos de
            patrimonio retornados em cada item.

    Returns:
        dict com:
        - `total`: total de bens encontrados antes da paginacao.
        - `resultados`: lista de bens; cada item pode incluir
          `unidade_responsavel`, `placa`, `descricao`, `classificacao`,
          `localizacao`, `status`, `situacao`, `tipo_ingresso`,
          `data_aquisicao`, `data_baixa`, `valor_ingresso` e
          `valor_atualizado`.
        - `metadata`: filtros aplicados, ordenacao, paginacao e campos pedidos.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhum bem for encontrado.
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
        schema_type=ConsultarPatrimoniosParams,
        on_error=lambda exc: ConsultarPatrimoniosResponse(
            total=0,
            resultados=[],
            metadata=ConsultarPatrimoniosMetadata(
                ordenar_por="data_aquisicao",
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
        registros = load_filtered_patrimonios(session, params.filtros)
        execution = execute_collection_lookup_result(
            registros,
            ordenar_por=params.ordenar_por,
            ordem=params.ordem,
            offset=params.offset,
            limite=params.limite,
            sort_key_getters=SORT_FIELD_GETTERS,
            empty_suggestion="Nenhum bem patrimonial encontrado com os filtros.",
        )

    metadata = ConsultarPatrimoniosMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_PATRIMONIO_FIELDS),
    )

    return build_lookup_response(
        response_type=ConsultarPatrimoniosResponse,
        metadata=metadata,
        execution=execution,
        project_row=project_patrimonio_fields,
        campos=params.campos,
        pagination_message_builder=lambda shown, total: (
            f"Mostrando {shown} de {total} bens encontrados."
        ),
    )
