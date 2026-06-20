"""Tool publica para consultar despesas detalhadas por veiculo de frota."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from agents.tools.names import ToolName
from agents.tools.registry import PUBLIC_SCOPE, register, routing_metadata
from agents.tools.sql_tools.shared.empty_state import resolve_empty_result_suggestion
from agents.tools.sql_tools.shared.validation import validate_tool_params
from database import session as session_manager
from database.models import FrotaDespesa, FrotaVeiculo
from database.session import _normalizar_texto
from shared.utils.decimal_to_float import decimal_to_float

from .consultar_despesas_frota_schema import (
    ALLOWED_DESPESAS_FROTA_FIELDS,
    ConsultarDespesasFrotaMetadata,
    ConsultarDespesasFrotaParams,
    ConsultarDespesasFrotaResponse,
    DespesasFrotaFiltroSchema,
)


def _load_despesas(session, filtros: DespesasFrotaFiltroSchema) -> list[FrotaDespesa]:
    stmt = (
        select(FrotaDespesa)
        .options(joinedload(FrotaDespesa.veiculo))
        .join(FrotaVeiculo, FrotaDespesa.veiculo_id == FrotaVeiculo.id)
    )
    if filtros.placa:
        normalized = _normalizar_texto(filtros.placa) or ""
        stmt = stmt.where(FrotaVeiculo.placa_veiculo.ilike(f"%{normalized}%"))
    if filtros.tipo_veiculo:
        normalized = _normalizar_texto(filtros.tipo_veiculo) or ""
        stmt = stmt.where(FrotaVeiculo.tipo_veiculo.ilike(f"%{normalized}%"))
    if filtros.tipo_despesa:
        normalized = _normalizar_texto(filtros.tipo_despesa) or ""
        stmt = stmt.where(FrotaDespesa.tipo_despesa.ilike(f"%{normalized}%"))
    if filtros.descricao:
        stmt = stmt.where(FrotaDespesa.descricao_evento.ilike(f"%{filtros.descricao}%"))
    if filtros.data_evento_inicio is not None:
        stmt = stmt.where(FrotaDespesa.data_evento >= filtros.data_evento_inicio)
    if filtros.data_evento_fim is not None:
        stmt = stmt.where(FrotaDespesa.data_evento <= filtros.data_evento_fim)
    return list(session.execute(stmt).unique().scalars())


def _sort_key(despesa: FrotaDespesa, ordenar_por: str) -> Any:
    veiculo = despesa.veiculo
    mapping = {
        "data_evento": despesa.data_evento,
        "total_despesa": despesa.total_despesa or Decimal(0),
        "valor_lancamento": despesa.valor_lancamento or Decimal(0),
        "placa_veiculo": (veiculo.placa_veiculo if veiculo else "") or "",
        "tipo_despesa": (despesa.tipo_despesa or "").lower(),
    }
    return mapping[ordenar_por]


def _row_to_public_dict(despesa: FrotaDespesa) -> dict[str, Any]:
    veiculo = despesa.veiculo
    return {
        "placa_veiculo": veiculo.placa_veiculo if veiculo else None,
        "tipo_veiculo": veiculo.tipo_veiculo if veiculo else None,
        "descricao_material": veiculo.descricao_material if veiculo else None,
        "unidade_gestora": veiculo.unidade_gestora if veiculo else None,
        "descricao_evento": despesa.descricao_evento,
        "tipo_despesa": despesa.tipo_despesa,
        "data_evento": despesa.data_evento.isoformat() if despesa.data_evento else None,
        "quantidade_lancamento": decimal_to_float(despesa.quantidade_lancamento),
        "valor_lancamento": decimal_to_float(despesa.valor_lancamento),
        "total_despesa": decimal_to_float(despesa.total_despesa),
    }


@register(
    name=ToolName.CONSULTAR_DESPESAS_FROTA,
    scope=PUBLIC_SCOPE,
    tags=["domain:frotas", "shape:lookup"],
    routing=routing_metadata(
        examples=[
            "Qual o historico de manutencao da ambulancia placa ABC-1234?",
            "Quais foram os gastos com a frota de onibus em 2025?",
            "Quantas manutencoes o veiculo X teve nos ultimos 12 meses?",
            "Quais despesas de combustivel a frota teve em 2024?",
        ],
        hints=[
            "historico manutencao",
            "despesa veiculo",
            "manutencao frota",
            "gasto frota",
            "combustivel frota",
            "evento frota",
            "reparo veiculo",
        ],
    ),
)
def consultar_despesas_frota(
    filtros: dict[str, Any] | None = None,
    ordenar_por: str = "data_evento",
    ordem: str = "desc",
    limite: int = 20,
    offset: int = 0,
    campos: list[str] | None = None,
) -> dict[str, Any]:
    """
    Lista despesas detalhadas (manutencoes, combustivel, etc.) por veiculo de frota.

    Cada registro expoe: placa, tipo de veiculo, unidade gestora, descricao do
    evento, tipo de despesa, data, quantidade lancada, valor lancado e total.
    Use esta tool para ver o historico de despesas de um veiculo especifico,
    ou para listar todos os gastos com um tipo de despesa (ex. combustivel).
    NAO use para dados cadastrais dos veiculos (marca, modelo, situacao); para
    isso use `consultar_frota`.
    NAO use para totais ou rankings de gasto por veiculo ou por tipo; para
    isso use `agregar_frota`.

    Args:
        filtros: Objeto com filtros opcionais. Campos aceitos: `placa`
            (match parcial na placa do veiculo), `tipo_veiculo`, `tipo_despesa`,
            `descricao` (texto do evento de manutencao), `data_evento_inicio` e
            `data_evento_fim` (formato `YYYY-MM-DD`).
        ordenar_por: Aceita `data_evento`, `total_despesa`, `valor_lancamento`,
            `placa_veiculo` ou `tipo_despesa`.
        ordem: Direcao da ordenacao: `asc` ou `desc`.
        limite: Tamanho da pagina. Inteiro de 1 a 100.
        offset: Deslocamento da pagina. Inteiro maior ou igual a 0.
        campos: Lista opcional com subconjunto dos campos publicos.

    Returns:
        dict com:
        - `total`: total de despesas encontradas antes da paginacao.
        - `resultados`: lista de despesas com dados do veiculo e do evento.
        - `metadata`: filtros aplicados, ordenacao e paginacao.
        - `mensagem`: aviso quando a resposta estiver paginada.
        - `sugestao`: dica quando nenhuma despesa for encontrada.
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
        schema_type=ConsultarDespesasFrotaParams,
        on_error=lambda exc: ConsultarDespesasFrotaResponse(
            total=0,
            resultados=[],
            metadata=ConsultarDespesasFrotaMetadata(
                ordenar_por="data_evento",
                ordem="desc",
                limite=20,
                offset=0,
            ),
            mensagem=f"Parametros invalidos: {exc}",
        ).model_dump(mode="json"),
    )
    if isinstance(validated, dict):
        return validated
    params = validated

    with session_manager.get_session() as session:
        despesas = _load_despesas(session, params.filtros)
        reverse = params.ordem == "desc"
        ordenados = sorted(despesas, key=lambda r: _sort_key(r, params.ordenar_por), reverse=reverse)
        total = len(ordenados)
        pagina = ordenados[params.offset : params.offset + params.limite]
        resultados = [_row_to_public_dict(r) for r in pagina]
        if params.campos:
            resultados = [{k: v for k, v in row.items() if k in params.campos} for row in resultados]
        empty_suggestion = resolve_empty_result_suggestion(
            session,
            domain_key="frota_despesas",
            filters=params.filtros,
            default_suggestion="Nenhuma despesa de frota encontrada com os filtros.",
        )

    metadata = ConsultarDespesasFrotaMetadata(
        filtros_aplicados=params.filtros.to_metadata_dict(),
        ordenar_por=params.ordenar_por,
        ordem=params.ordem,
        limite=params.limite,
        offset=params.offset,
        campos=params.campos or list(ALLOWED_DESPESAS_FROTA_FIELDS),
    )

    mensagem = None
    if total > params.offset + len(resultados):
        mensagem = f"Exibindo {len(resultados)} de {total} despesas. Use limite e offset para navegar."

    return ConsultarDespesasFrotaResponse(
        total=total,
        resultados=resultados,
        metadata=metadata,
        mensagem=mensagem,
        sugestao=(empty_suggestion if not resultados else None),
    ).model_dump(mode="json")
