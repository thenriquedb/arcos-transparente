"""Helpers SQL compartilhados pelas tools de secretaria."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select

from database.models import Servidor


def _construir_subquery_secretaria(
    *,
    termo_normalizado: str,
    competencia_referencia: date,
):
    return (
        select(func.max(Servidor.id).label("id"))
        .where(Servidor.competencia_referencia == competencia_referencia)
        .where(func.lower(Servidor.secretaria).like(f"%{termo_normalizado}%"))
        .group_by(func.lower(Servidor.nome), func.lower(Servidor.secretaria))
        .subquery()
    )


def listar_secretarias_correspondentes(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
) -> list[str]:
    return (
        session.execute(
            select(Servidor.secretaria)
            .where(Servidor.competencia_referencia == competencia_referencia)
            .where(func.lower(Servidor.secretaria).like(f"%{termo_normalizado}%"))
            .group_by(Servidor.secretaria)
            .order_by(Servidor.secretaria.asc())
        )
        .scalars()
        .all()
    )


def contar_servidores_por_secretaria_na_competencia(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
) -> int:
    subquery = _construir_subquery_secretaria(
        termo_normalizado=termo_normalizado,
        competencia_referencia=competencia_referencia,
    )
    return session.execute(select(func.count()).select_from(subquery)).scalar_one()


def listar_servidores_por_secretaria_na_competencia(
    session,
    *,
    termo_normalizado: str,
    competencia_referencia: date,
    limite: int,
) -> list[Servidor]:
    subquery = _construir_subquery_secretaria(
        termo_normalizado=termo_normalizado,
        competencia_referencia=competencia_referencia,
    )
    return (
        session.execute(
            select(Servidor)
            .join(subquery, Servidor.id == subquery.c.id)
            .order_by(Servidor.secretaria.asc(), Servidor.nome.asc())
            .limit(limite)
        )
        .scalars()
        .all()
    )
