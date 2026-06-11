"""Helpers SQL compartilhados para consultas amplas de contratos."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, inspect, or_

from database.models import Contrato
from database.session import _normalizar_texto

from .filters import ContratosFiltroSchema
from .responses import ContratoToolItem
from .runtime import serializar_contrato


GROUP_BY_COLUMNS = {
    "secretaria": Contrato.secretaria,
    "categoria": Contrato.categoria,
    "fornecedor": Contrato.fornecedor,
    "ano_inicio": func.strftime("%Y", Contrato.data_inicio),
}
SEARCH_FIELD_LABELS = {
    "numero": "numero",
    "fornecedor": "fornecedor",
    "descricao": "descricao",
    "categoria": "categoria",
    "secretaria": "secretaria",
}
SHORT_TEXT_TERM_MAX_LENGTH = 3


def get_contratos_available_columns(session) -> set[str]:
    """Lista colunas existentes na tabela `contratos` na base atual."""

    inspector = inspect(session.bind)
    return {column["name"] for column in inspector.get_columns("contratos")}


def contratos_supports_descricao_despesa(session) -> bool:
    """Verifica se a base atual ja possui a coluna `descricao_despesa`."""

    return "descricao_despesa" in get_contratos_available_columns(session)


def contratos_supports_xml_original(session) -> bool:
    """Verifica se a base atual ja possui a coluna `xml_original`."""

    return "xml_original" in get_contratos_available_columns(session)


def contratos_supports_detalhes_completos(session) -> bool:
    """Verifica se as tabelas filhas de contratos ja existem na base atual."""

    inspector = inspect(session.bind)
    tabelas = set(inspector.get_table_names())
    return {
        "contrato_despesas_orcamentarias",
        "contrato_itens_adquiridos",
    }.issubset(tabelas)


def build_descricao_despesa_unavailable_message(
    filtros: ContratosFiltroSchema,
) -> str | None:
    """Explica quando uma busca textual pode estar incompleta em base antiga."""

    if filtros.descricao is None:
        return None
    return (
        "A classificacao da despesa ainda nao esta disponivel nesta base atual. "
        "Para incluir buscas por termos como esse, aplique as migrations e "
        "reimporte contratos."
    )


def build_contrato_details_unavailable_message() -> str:
    """Explica quando detalhes completos do contrato ainda nao existem na base."""

    return (
        "Os detalhes completos do contrato ainda nao estao disponiveis nesta base "
        "atual. Aplique as migrations e reimporte contratos para carregar despesas "
        "orcamentarias e itens adquiridos."
    )


def build_contract_fallback_message(source_field: str, target_field: str) -> str:
    """Explica de forma simples quando a consulta precisou trocar de coluna."""

    source_label = SEARCH_FIELD_LABELS.get(source_field, source_field)
    target_label = SEARCH_FIELD_LABELS.get(target_field, target_field)
    return f"Nenhum contrato foi encontrado por {source_label}. Exibindo resultados relacionados por {target_label}."


def _apply_numero_filter(stmt, numero: str, available_columns: set[str] | None):
    """Busca o numero tambem nas colunas alternativas quando existem na base."""

    pattern = f"%{numero.lower()}%"
    numero_expressions = [func.lower(func.coalesce(Contrato.numero, "")).like(pattern)]
    if available_columns is not None:
        if "numero_licitatorio" in available_columns:
            numero_expressions.append(func.lower(func.coalesce(Contrato.numero_licitatorio, "")).like(pattern))
        if "numero_instrumento" in available_columns:
            numero_expressions.append(func.lower(func.coalesce(Contrato.numero_instrumento, "")).like(pattern))
    return stmt.where(or_(*numero_expressions))


def _apply_descricao_filter(
    stmt,
    descricao: str,
    *,
    include_descricao_despesa: bool,
    include_xml_original: bool,
):
    for term in _normalized_filter_terms(descricao):
        descricao_expressions = [_text_contains_term(Contrato.descricao, term)]
        if include_descricao_despesa:
            descricao_expressions.append(_text_contains_term(Contrato.descricao_despesa, term))

        # O XML bruto entra apenas como ultimo apoio para nao perder termos
        # existentes no portal que ainda nao viraram colunas estruturadas.
        if include_xml_original:
            descricao_expressions.append(_text_contains_term(Contrato.xml_original, term))
        stmt = stmt.where(or_(*descricao_expressions))
    return stmt


def _apply_date_filters(stmt, filtros: ContratosFiltroSchema):
    if filtros.data_inicio is not None:
        stmt = stmt.where(Contrato.data_inicio == filtros.data_inicio)
    elif filtros.data_inicio_inicio is not None and filtros.data_inicio_fim is not None:
        stmt = stmt.where(
            Contrato.data_inicio.between(
                filtros.data_inicio_inicio,
                filtros.data_inicio_fim,
            )
        )
    if filtros.data_fim is not None:
        stmt = stmt.where(Contrato.data_fim == filtros.data_fim)
    elif filtros.data_fim_inicio is not None and filtros.data_fim_fim is not None:
        stmt = stmt.where(
            Contrato.data_fim.between(
                filtros.data_fim_inicio,
                filtros.data_fim_fim,
            )
        )
    if filtros.vigente_em is not None:
        # Vigência: começou até a data e ainda não terminou (fim em aberto vale).
        stmt = stmt.where(Contrato.data_inicio <= filtros.vigente_em)
        stmt = stmt.where(
            or_(
                Contrato.data_fim.is_(None),
                Contrato.data_fim >= filtros.vigente_em,
            )
        )
    return stmt


def apply_contratos_filters(
    stmt,
    filtros: ContratosFiltroSchema,
    *,
    include_descricao_despesa: bool = True,
    include_xml_original: bool = False,
    available_columns: set[str] | None = None,
):
    """Aplica os filtros publicos de contratos sobre o statement SQL."""

    if filtros.numero:
        stmt = _apply_numero_filter(stmt, filtros.numero, available_columns)
    if filtros.fornecedor:
        for term in _normalized_filter_terms(filtros.fornecedor):
            stmt = stmt.where(_text_contains_term(Contrato.fornecedor, term))
    if filtros.documento_fornecedor:
        stmt = stmt.where(func.lower(Contrato.cnpj).like(f"%{filtros.documento_fornecedor.lower()}%"))
    if filtros.categoria:
        for term in _normalized_filter_terms(filtros.categoria):
            stmt = stmt.where(_text_contains_term(Contrato.categoria, term))
    if filtros.secretaria:
        for term in _normalized_filter_terms(filtros.secretaria):
            stmt = stmt.where(_text_contains_term(Contrato.secretaria, term))
    if filtros.descricao:
        stmt = _apply_descricao_filter(
            stmt,
            filtros.descricao,
            include_descricao_despesa=include_descricao_despesa,
            include_xml_original=include_xml_original,
        )
    stmt = _apply_date_filters(stmt, filtros)
    if filtros.valor_min is not None:
        stmt = stmt.where(Contrato.valor >= filtros.valor_min)
    if filtros.valor_max is not None:
        stmt = stmt.where(Contrato.valor <= filtros.valor_max)
    return stmt


def _normalized_filter_terms(value: str) -> list[str]:
    return (_normalizar_texto(value) or "").split()


def _text_contains_term(column, term: str):
    normalized_column = func.normalizar(func.coalesce(column, ""))
    if len(term) <= SHORT_TEXT_TERM_MAX_LENGTH and term.isalnum():
        return or_(
            normalized_column == term,
            normalized_column.op("GLOB")(f"{term}[^0-9a-z]*"),
            normalized_column.op("GLOB")(f"*[^0-9a-z]{term}"),
            normalized_column.op("GLOB")(f"*[^0-9a-z]{term}[^0-9a-z]*"),
        )
    return normalized_column.like(f"%{term}%")


def project_contrato_fields(
    contrato: Contrato | Mapping[str, Any],
    campos: list[str],
) -> dict[str, Any]:
    """Projeta o registro nos campos publicos solicitados."""

    if isinstance(contrato, Mapping):
        raw_payload = dict(contrato)
        serialized = ContratoToolItem.model_validate(raw_payload).model_dump(mode="json")
        for key, value in raw_payload.items():
            if key not in serialized:
                serialized[key] = value
    else:
        serialized = serializar_contrato(contrato)
    if not campos:
        return serialized
    return {campo: serialized[campo] for campo in campos}
