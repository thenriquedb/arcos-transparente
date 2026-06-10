"""Utilitarios compartilhados de serializacao das tools de servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select

from database.models import FolhaServidor
from shared.utils.decimal_to_float import decimal_to_float

from .responses import ServidorToolItem


def serializar_servidor(servidor: FolhaServidor) -> dict[str, Any]:
    """Serializa o modelo ORM em payload padronizado para as tools."""

    payload = ServidorToolItem.model_validate(
        {
            "id": servidor.id,
            "nome": servidor.nome,
            "cargo": servidor.cargo,
            "secretaria": servidor.secretaria,
            "salario_base": decimal_to_float(servidor.salario_base),
            "mes_de_referencia": servidor.competencia_referencia,
        }
    )
    return payload.model_dump(mode="json")


def obter_mes_de_referencia_mais_recente(session) -> date | None:
    return session.execute(select(func.max(FolhaServidor.competencia_referencia))).scalar_one_or_none()
