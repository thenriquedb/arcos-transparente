"""Helpers SQL compartilhados para consultas amplas de contratos."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from sqlalchemy import func, inspect, or_

from database.models import Contrato
from shared.utils.decimal_to_float import decimal_to_float

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
    return (
        f"Nenhum contrato foi encontrado por {source_label}. "
        f"Exibindo resultados relacionados por {target_label}."
    )


def apply_contratos_filters(
    stmt,
    filtros: ContratosFiltroSchema,
    *,
    include_descricao_despesa: bool = True,
    include_xml_original: bool = False,
    available_columns: set[str] | None = None,
):
    if filtros.numero:
        numero_expressions = [
            func.lower(func.coalesce(Contrato.numero, "")).like(
                f"%{filtros.numero.lower()}%"
            )
        ]
        if available_columns is not None:
            if "numero_licitatorio" in available_columns:
                numero_expressions.append(
                    func.lower(func.coalesce(Contrato.numero_licitatorio, "")).like(
                        f"%{filtros.numero.lower()}%"
                    )
                )
            if "numero_instrumento" in available_columns:
                numero_expressions.append(
                    func.lower(func.coalesce(Contrato.numero_instrumento, "")).like(
                        f"%{filtros.numero.lower()}%"
                    )
                )
        stmt = stmt.where(or_(*numero_expressions))
    if filtros.fornecedor:
        for term in filtros.fornecedor.lower().split():
            stmt = stmt.where(func.lower(Contrato.fornecedor).like(f"%{term}%"))
    if filtros.documento_fornecedor:
        stmt = stmt.where(
            func.lower(Contrato.cnpj).like(f"%{filtros.documento_fornecedor.lower()}%")
        )
    if filtros.categoria:
        stmt = stmt.where(
            func.lower(Contrato.categoria).like(f"%{filtros.categoria.lower()}%")
        )
    if filtros.secretaria:
        stmt = stmt.where(
            func.lower(Contrato.secretaria).like(f"%{filtros.secretaria.lower()}%")
        )
    if filtros.descricao:
        for term in filtros.descricao.lower().split():
            descricao_expressions = [
                func.lower(func.coalesce(Contrato.descricao, "")).like(f"%{term}%")
            ]
            if include_descricao_despesa:
                descricao_expressions.append(
                    func.lower(func.coalesce(Contrato.descricao_despesa, "")).like(
                        f"%{term}%"
                    )
                )

            # O XML bruto entra apenas como ultimo apoio para nao perder termos
            # existentes no portal que ainda nao viraram colunas estruturadas.
            if include_xml_original:
                descricao_expressions.append(
                    func.lower(func.coalesce(Contrato.xml_original, "")).like(
                        f"%{term}%"
                    )
                )
            stmt = stmt.where(or_(*descricao_expressions))
    if filtros.data_inicio is not None:
        stmt = stmt.where(Contrato.data_inicio == filtros.data_inicio)
    elif filtros.data_inicio_inicio is not None and filtros.data_inicio_fim is not None:
        stmt = stmt.where(
            Contrato.data_inicio.between(
                filtros.data_inicio_inicio,
                filtros.data_inicio_fim,
            )
        )
    if filtros.valor_min is not None:
        stmt = stmt.where(Contrato.valor >= filtros.valor_min)
    if filtros.valor_max is not None:
        stmt = stmt.where(Contrato.valor <= filtros.valor_max)
    return stmt


def project_contrato_fields(
    contrato: Contrato | Mapping[str, Any],
    campos: list[str],
) -> dict[str, Any]:
    if isinstance(contrato, Mapping):
        raw_payload = dict(contrato)
        serialized = ContratoToolItem.model_validate(raw_payload).model_dump(
            mode="json"
        )
        for key, value in raw_payload.items():
            if key not in serialized:
                serialized[key] = value
    else:
        serialized = serializar_contrato(contrato)
    if not campos:
        return serialized
    return {campo: serialized[campo] for campo in campos}


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
