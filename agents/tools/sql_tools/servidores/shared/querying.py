"""Helpers SQL compartilhados para consultas amplas de servidores."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func

from database.session import _normalizar_texto
from database.models import FolhaServidor
from agents.tools.sql_tools.shared.projection import project_public_fields
from shared.utils.decimal_to_float import decimal_to_float

from .filters import ServidoresFiltroSchema
from .runtime import obter_mes_de_referencia_mais_recente, serializar_servidor


def resolve_mes_de_referencia_padrao(
    session,
    filtros: ServidoresFiltroSchema,
) -> tuple[object | None, bool]:
    if filtros.mes_de_referencia is not None:
        return filtros.mes_de_referencia, False
    if (
        filtros.mes_de_referencia_inicio is not None
        and filtros.mes_de_referencia_fim is not None
    ):
        return None, False

    mes_de_referencia = obter_mes_de_referencia_mais_recente(session)
    return mes_de_referencia, mes_de_referencia is not None


def apply_servidores_filters(
    stmt,
    filtros: ServidoresFiltroSchema,
    *,
    mes_de_referencia_considerado,
):
    if mes_de_referencia_considerado is not None:
        stmt = stmt.where(
            FolhaServidor.competencia_referencia == mes_de_referencia_considerado
        )
    elif (
        filtros.mes_de_referencia_inicio is not None
        and filtros.mes_de_referencia_fim is not None
    ):
        stmt = stmt.where(
            FolhaServidor.competencia_referencia.between(
                filtros.mes_de_referencia_inicio,
                filtros.mes_de_referencia_fim,
            )
        )

    if filtros.nome:
        for term in (_normalizar_texto(filtros.nome) or "").split():
            stmt = _apply_text_contains_filter(stmt, FolhaServidor.nome, term)
    if filtros.secretaria:
        stmt = _apply_text_contains_filter(
            stmt, FolhaServidor.secretaria, filtros.secretaria
        )
    if filtros.cargo:
        stmt = _apply_text_contains_filter(stmt, FolhaServidor.cargo, filtros.cargo)
    if filtros.salario_min is not None:
        stmt = stmt.where(FolhaServidor.salario_base >= filtros.salario_min)
    if filtros.salario_max is not None:
        stmt = stmt.where(FolhaServidor.salario_base <= filtros.salario_max)
    return stmt


def _apply_text_contains_filter(stmt, column, value: str):
    normalized = _normalizar_texto(value)
    if not normalized:
        return stmt
    return stmt.where(func.normalizar(column).like(f"%{normalized}%"))


def project_servidor_fields(
    servidor: FolhaServidor,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        servidor,
        campos,
        serializer=serializar_servidor,
        order="requested",
    )


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
