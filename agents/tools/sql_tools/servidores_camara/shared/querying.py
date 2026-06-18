"""Helpers SQL compartilhados para consultas de servidores da Camara."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func

from agents.tools.sql_tools.shared.projection import project_public_fields
from database.models import ServidorCamara
from database.session import _normalizar_texto

from .filters import ServidorCamaraFiltroSchema
from .runtime import obter_mes_de_referencia_mais_recente_camara, serializar_servidor_camara


def resolve_mes_de_referencia_padrao_camara(
    session,
    filtros: ServidorCamaraFiltroSchema,
) -> tuple[object | None, bool]:
    if filtros.mes_de_referencia is not None:
        return filtros.mes_de_referencia, False
    if filtros.mes_de_referencia_inicio is not None and filtros.mes_de_referencia_fim is not None:
        return None, False
    mes = obter_mes_de_referencia_mais_recente_camara(session)
    return mes, mes is not None


def apply_servidores_camara_filters(
    stmt,
    filtros: ServidorCamaraFiltroSchema,
    *,
    mes_de_referencia_considerado,
):
    """Aplica os filtros publicos do dominio sobre a consulta de servidores da Camara."""

    if mes_de_referencia_considerado is not None:
        stmt = stmt.where(ServidorCamara.competencia_referencia == mes_de_referencia_considerado)
    elif filtros.mes_de_referencia_inicio is not None and filtros.mes_de_referencia_fim is not None:
        stmt = stmt.where(
            ServidorCamara.competencia_referencia.between(
                filtros.mes_de_referencia_inicio,
                filtros.mes_de_referencia_fim,
            )
        )

    if filtros.nome:
        for term in (_normalizar_texto(filtros.nome) or "").split():
            stmt = stmt.where(func.normalizar(ServidorCamara.nome).like(f"%{term}%"))
    if filtros.cargo:
        normalized = _normalizar_texto(filtros.cargo)
        if normalized:
            stmt = stmt.where(func.normalizar(ServidorCamara.cargo).like(f"%{normalized}%"))
    if filtros.lotacao:
        normalized = _normalizar_texto(filtros.lotacao)
        if normalized:
            stmt = stmt.where(func.normalizar(ServidorCamara.lotacao).like(f"%{normalized}%"))
    if filtros.situacao_funcional:
        normalized = _normalizar_texto(filtros.situacao_funcional)
        if normalized:
            stmt = stmt.where(func.normalizar(ServidorCamara.situacao_funcional).like(f"%{normalized}%"))
    if filtros.vinculo:
        normalized = _normalizar_texto(filtros.vinculo)
        if normalized:
            stmt = stmt.where(func.normalizar(ServidorCamara.vinculo).like(f"%{normalized}%"))
    if filtros.salario_min is not None:
        stmt = stmt.where(ServidorCamara.salario_base >= filtros.salario_min)
    if filtros.salario_max is not None:
        stmt = stmt.where(ServidorCamara.salario_base <= filtros.salario_max)

    return stmt


def project_servidor_camara_fields(
    servidor: ServidorCamara,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        servidor,
        campos,
        serializer=serializar_servidor_camara,
        order="requested",
    )
