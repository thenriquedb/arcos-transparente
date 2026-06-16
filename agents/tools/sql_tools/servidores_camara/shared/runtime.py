"""Utilitarios de runtime das tools de servidores da Camara."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select

from database.models import ServidorCamara
from shared.utils.decimal_to_float import decimal_to_float


def obter_mes_de_referencia_mais_recente_camara(session) -> date | None:
    return session.execute(select(func.max(ServidorCamara.competencia_referencia))).scalar_one_or_none()


def serializar_servidor_camara(servidor: ServidorCamara) -> dict[str, Any]:
    return {
        "id": servidor.id,
        "nome": servidor.nome,
        "matricula": servidor.matricula,
        "cargo": servidor.cargo,
        "lotacao": servidor.lotacao,
        "situacao_funcional": servidor.situacao_funcional,
        "salario_base": decimal_to_float(servidor.salario_base),
        "proventos": decimal_to_float(servidor.proventos),
        "descontos": decimal_to_float(servidor.descontos),
        "liquido": decimal_to_float(servidor.liquido),
        "mes_de_referencia": servidor.competencia_referencia.isoformat() if servidor.competencia_referencia else None,
    }
