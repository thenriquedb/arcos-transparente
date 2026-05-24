"""Utilitarios compartilhados de serializacao e resposta das tools de servidores."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select

from database.models import Servidor
from shared.utils.decimal_to_float import decimal_to_float

from .responses import ServidorToolItem, ServidoresToolResponse


def serializar_servidor(servidor: Servidor) -> dict[str, Any]:
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
    return session.execute(
        select(func.max(Servidor.competencia_referencia))
    ).scalar_one_or_none()


def resposta_sem_resultados(
    *,
    query: str | None = None,
    data_inicio: Any | None = None,
    data_fim: Any | None = None,
    mes_de_referencia: Any | None = None,
    secretarias_correspondentes: list[str] | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, Any]:
    return ServidoresToolResponse(
        query=query,
        data_inicio=data_inicio,
        data_fim=data_fim,
        mes_de_referencia=mes_de_referencia,
        total=0,
        resultados=[],
        secretarias_correspondentes=secretarias_correspondentes or [],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")
