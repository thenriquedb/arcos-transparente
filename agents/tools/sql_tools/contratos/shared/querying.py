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


def contratos_supports_descricao_despesa(session) -> bool:
    """Verifica se a base atual ja possui a coluna `descricao_despesa`."""

    inspector = inspect(session.bind)
    return any(
        column["name"] == "descricao_despesa"
        for column in inspector.get_columns("contratos")
    )


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


def apply_contratos_filters(
    stmt,
    filtros: ContratosFiltroSchema,
    *,
    include_descricao_despesa: bool = True,
):
    if filtros.numero:
        stmt = stmt.where(
            func.lower(Contrato.numero).like(f"%{filtros.numero.lower()}%")
        )
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
            if include_descricao_despesa:
                stmt = stmt.where(
                    or_(
                        func.lower(func.coalesce(Contrato.descricao, "")).like(
                            f"%{term}%"
                        ),
                        func.lower(func.coalesce(Contrato.descricao_despesa, "")).like(
                            f"%{term}%"
                        ),
                    )
                )
            else:
                stmt = stmt.where(
                    func.lower(func.coalesce(Contrato.descricao, "")).like(
                        f"%{term}%"
                    )
                )
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
        serialized = ContratoToolItem.model_validate(dict(contrato)).model_dump(
            mode="json"
        )
    else:
        serialized = serializar_contrato(contrato)
    if not campos:
        return serialized
    return {campo: serialized[campo] for campo in campos}


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
