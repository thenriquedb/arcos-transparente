"""Helpers de consulta para receitas."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database.models import ReceitaArrecadacao, ReceitaLancamento
from shared.utils.text import matches_text_query, normalize_search_text

from .filters import ReceitaFiltroSchema
from .runtime import serializar_receita_arrecadacao, serializar_receita_lancamento


TEXT_FILTER_FIELDS = {
    "unidade_responsavel": ("unidade_responsavel",),
    "categoria": ("categoria",),
    "categoria_codigo": ("categoria_codigo",),
    "tipo": ("tipo",),
    "tributo": ("tributo",),
    "origem_do_recurso": ("origem_do_recurso",),
}

THEME_SEARCH_FIELDS = (
    "unidade_responsavel",
    "categoria_codigo",
    "categoria",
    "tipo",
    "tributo",
    "origem_do_recurso",
)

SORT_FIELD_GETTERS = {
    "ano": lambda row: row.get("ano") or 0,
    "mes_num": lambda row: row.get("mes_num") or 0,
    "data": lambda row: row.get("data") or "",
    "unidade_responsavel": lambda row: row.get("unidade_responsavel") or "",
    "categoria": lambda row: row.get("categoria") or "",
    "tipo": lambda row: row.get("tipo") or "",
    "tributo": lambda row: row.get("tributo") or "",
    "valor_previsto": lambda row: row.get("valor_previsto") or 0.0,
    "valor_recebido": lambda row: row.get("valor_recebido") or 0.0,
    "valor_lancado": lambda row: row.get("valor_lancado") or 0.0,
    "valor_em_divida_ativa": lambda row: row.get("valor_em_divida_ativa") or 0.0,
    "valor_em_cobranca_judicial": (lambda row: row.get("valor_em_cobranca_judicial") or 0.0),
}

GROUP_FIELD_GETTERS = {
    "mes": lambda row: row.get("mes"),
    "unidade_responsavel": lambda row: row.get("unidade_responsavel"),
    "categoria": lambda row: row.get("categoria"),
    "tipo": lambda row: row.get("tipo"),
    "tributo": lambda row: row.get("tributo"),
    "origem_do_recurso": lambda row: row.get("origem_do_recurso"),
}

METRIC_FIELD_GETTERS = {
    "soma_valor_previsto": lambda row: row.get("valor_previsto") or 0.0,
    "soma_valor_recebido": lambda row: row.get("valor_recebido") or 0.0,
    "soma_valor_lancado": lambda row: row.get("valor_lancado") or 0.0,
    "soma_valor_em_divida_ativa": (lambda row: row.get("valor_em_divida_ativa") or 0.0),
    "soma_valor_em_cobranca_judicial": (lambda row: row.get("valor_em_cobranca_judicial") or 0.0),
}

RECEITA_TEMA_ALIASES = {
    "iptu": ("iptu", "imposto predial e territorial"),
    "iss": ("iss", "issqn", "imposto sobre servicos"),
    "issqn": ("issqn", "iss", "imposto sobre servicos"),
    "itbi": ("itbi",),
    "ipva": ("ipva",),
    "fundeb": ("fundeb",),
    "enfermagem": ("enfermagem",),
}


def _get_search_terms(query: str | None) -> tuple[str, ...]:
    normalized = normalize_search_text(query).strip()
    if not normalized:
        return ()
    return RECEITA_TEMA_ALIASES.get(normalized, (query or "",))


def _matches_fields(record: dict[str, object], field_names: tuple[str, ...], query: str) -> bool:
    search_terms = _get_search_terms(query)
    return any(
        matches_text_query(str(record.get(field_name) or ""), search_term)
        for field_name in field_names
        for search_term in search_terms
    )


def _match_receita_filters(record: dict[str, object], filtros: ReceitaFiltroSchema) -> bool:
    if filtros.ano is not None and record.get("ano") != filtros.ano:
        return False
    if filtros.mes is not None and record.get("mes_num") != filtros.mes:
        return False
    if filtros.mes_inicio is not None and filtros.mes_fim is not None:
        mes_num = record.get("mes_num") or 0
        if not filtros.mes_inicio <= mes_num <= filtros.mes_fim:
            return False

    for filtro_nome, field_names in TEXT_FILTER_FIELDS.items():
        query = getattr(filtros, filtro_nome)
        if query and not _matches_fields(record, field_names, query):
            return False

    if filtros.tema and not _matches_fields(record, THEME_SEARCH_FIELDS, filtros.tema):
        return False

    metric_value = 0.0
    if filtros.tipo_de_dado == "arrecadacao":
        metric_value = record.get("valor_recebido") or 0.0
    elif filtros.tipo_de_dado == "lancamento":
        metric_value = record.get("valor_lancado") or 0.0

    if filtros.valor_min is not None and metric_value < float(filtros.valor_min):
        return False
    if filtros.valor_max is not None and metric_value > float(filtros.valor_max):
        return False
    return True


def load_filtered_receitas(session, filtros: ReceitaFiltroSchema) -> list[dict[str, object]]:
    """Carrega os registros do dominio aplicando os filtros publicos."""

    if filtros.tipo_de_dado == "lancamento":
        registros = session.execute(select(ReceitaLancamento)).scalars().all()
        serializados = [serializar_receita_lancamento(registro) for registro in registros]
    else:
        stmt = select(ReceitaArrecadacao).options(selectinload(ReceitaArrecadacao.natureza))
        registros = session.execute(stmt).scalars().all()
        serializados = [serializar_receita_arrecadacao(registro) for registro in registros]

    return [registro for registro in serializados if _match_receita_filters(registro, filtros)]
