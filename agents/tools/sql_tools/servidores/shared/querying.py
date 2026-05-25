"""Helpers SQL compartilhados para consultas amplas de servidores."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func

from database.models import Servidor
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
        stmt = stmt.where(Servidor.competencia_referencia == mes_de_referencia_considerado)
    elif (
        filtros.mes_de_referencia_inicio is not None
        and filtros.mes_de_referencia_fim is not None
    ):
        stmt = stmt.where(
            Servidor.competencia_referencia.between(
                filtros.mes_de_referencia_inicio,
                filtros.mes_de_referencia_fim,
            )
        )

    if filtros.nome:
        for term in filtros.nome.lower().split():
            stmt = stmt.where(func.lower(Servidor.nome).like(f"%{term}%"))
    if filtros.secretaria:
        stmt = stmt.where(
            func.lower(Servidor.secretaria).like(f"%{filtros.secretaria.lower()}%")
        )
    if filtros.cargo:
        stmt = stmt.where(func.lower(Servidor.cargo).like(f"%{filtros.cargo.lower()}%"))
    if filtros.salario_min is not None:
        stmt = stmt.where(Servidor.salario_base >= filtros.salario_min)
    if filtros.salario_max is not None:
        stmt = stmt.where(Servidor.salario_base <= filtros.salario_max)
    return stmt


def project_servidor_fields(
    servidor: Servidor,
    campos: list[str],
) -> dict[str, Any]:
    serialized = serializar_servidor(servidor)
    if not campos:
        return serialized
    return {campo: serialized[campo] for campo in campos}


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
