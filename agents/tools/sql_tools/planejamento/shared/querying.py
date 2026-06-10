"""Helpers de consulta para planejamento."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select

from database.models import PlanejamentoDespesa
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.text import matches_text_query

from shared.planejamento_entidades import get_planejamento_entidade_search_terms
from .filters import PlanejamentoFiltroSchema


TEXT_FILTER_FIELDS = {
    "area": "funcao",
    "subarea": "subfuncao",
    "programa": "programa",
    "acao": "descricao_acao",
    "grupo_de_gasto": "grupo_despesa_descricao",
    "categoria_de_gasto": "categoria_economica_descricao",
    "fonte_recurso": "fonte_recurso_descricao",
}

ENTIDADE_TEXT_FIELDS = (
    "programa",
    "unidade_gestora",
    "orgao",
    "unidade",
)

SORT_FIELD_GETTERS = {
    "ano": lambda row: row.exercicio,
    "mes_num": lambda row: row.mes_num,
    "area": lambda row: row.funcao or "",
    "subarea": lambda row: row.subfuncao or "",
    "programa": lambda row: row.programa or "",
    "acao": lambda row: row.descricao_acao or "",
    "grupo_de_gasto": lambda row: row.grupo_despesa_descricao or "",
    "orcamento_inicial": lambda row: row.dotacao_inicial or Decimal("0"),
    "orcamento_atualizado": lambda row: row.dotacao_atualizada or Decimal("0"),
    "valor_comprometido": lambda row: row.valor_empenhado or Decimal("0"),
    "valor_confirmado": lambda row: row.valor_liquidado or Decimal("0"),
    "valor_pago": lambda row: row.valor_pago or Decimal("0"),
    "valor_cancelado": lambda row: row.valor_anulado or Decimal("0"),
}

GROUP_FIELD_GETTERS = {
    "mes": lambda row: row.mes,
    "area": lambda row: row.funcao,
    "subarea": lambda row: row.subfuncao,
    "programa": lambda row: row.programa,
    "acao": lambda row: row.descricao_acao,
    "grupo_de_gasto": lambda row: row.grupo_despesa_descricao,
    "categoria_de_gasto": lambda row: row.categoria_economica_descricao,
    "fonte_recurso": lambda row: row.fonte_recurso_descricao,
}

METRIC_FIELD_GETTERS = {
    "soma_orcamento_inicial": lambda row: row.dotacao_inicial,
    "soma_orcamento_atualizado": lambda row: row.dotacao_atualizada,
    "soma_valor_comprometido": lambda row: row.valor_empenhado,
    "soma_valor_confirmado": lambda row: row.valor_liquidado,
    "soma_valor_pago": lambda row: row.valor_pago,
    "soma_valor_cancelado": lambda row: row.valor_anulado,
}


def apply_planejamento_sql_filters(stmt, filtros: PlanejamentoFiltroSchema):
    """Aplica os filtros publicos do dominio sobre a consulta."""

    if filtros.origem:
        stmt = stmt.where(PlanejamentoDespesa.origem == filtros.origem)
    if filtros.ano is not None:
        stmt = stmt.where(PlanejamentoDespesa.exercicio == filtros.ano)
    if filtros.mes is not None:
        stmt = stmt.where(PlanejamentoDespesa.mes_num == filtros.mes)
    elif filtros.mes_inicio is not None and filtros.mes_fim is not None:
        stmt = stmt.where(PlanejamentoDespesa.mes_num.between(filtros.mes_inicio, filtros.mes_fim))
    if filtros.valor_pago_min is not None:
        stmt = stmt.where(PlanejamentoDespesa.valor_pago >= filtros.valor_pago_min)
    if filtros.valor_pago_max is not None:
        stmt = stmt.where(PlanejamentoDespesa.valor_pago <= filtros.valor_pago_max)
    return stmt


def matches_planejamento_text_filters(
    registro: PlanejamentoDespesa,
    filtros: PlanejamentoFiltroSchema,
) -> bool:
    entidade_search_terms = get_planejamento_entidade_search_terms(filtros.entidade)
    if entidade_search_terms and not any(
        matches_text_query(getattr(registro, attr_name), search_term)
        for attr_name in ENTIDADE_TEXT_FIELDS
        for search_term in entidade_search_terms
    ):
        return False

    for filtro_nome, attr_name in TEXT_FILTER_FIELDS.items():
        query = getattr(filtros, filtro_nome)
        if query and not matches_text_query(getattr(registro, attr_name), query):
            return False
    return True


def load_filtered_planejamentos(session, filtros: PlanejamentoFiltroSchema):
    """Carrega os registros do dominio aplicando os filtros publicos."""

    stmt = apply_planejamento_sql_filters(select(PlanejamentoDespesa), filtros)
    registros = session.execute(stmt).scalars().all()
    return [registro for registro in registros if matches_planejamento_text_filters(registro, filtros)]


def metric_to_json(value: int | Decimal) -> int | float:
    if isinstance(value, Decimal):
        return decimal_to_float(value) or 0.0
    return value
