"""Serializacao publica das tools de planejamento."""

from __future__ import annotations

from typing import Any

from agents.tools.sql_tools.shared.projection import project_public_fields
from database.models import PlanejamentoDespesa
from shared.utils.decimal_to_float import decimal_to_float


def serializar_planejamento(registro: PlanejamentoDespesa) -> dict[str, Any]:
    return {
        "id": registro.id,
        "origem": registro.origem,
        "ano": registro.exercicio,
        "mes": registro.mes,
        "mes_num": registro.mes_num,
        "unidade_gestora": registro.unidade_gestora,
        "orgao": registro.orgao,
        "unidade": registro.unidade,
        "area": registro.funcao,
        "subarea": registro.subfuncao,
        "programa": registro.programa,
        "tipo_acao": registro.tipo_acao,
        "acao": registro.descricao_acao,
        "fonte_recurso": registro.fonte_recurso_descricao,
        "esfera": registro.esfera_administrativa,
        "categoria_de_gasto": registro.categoria_economica_descricao,
        "grupo_de_gasto": registro.grupo_despesa_descricao,
        "orcamento_inicial": decimal_to_float(registro.dotacao_inicial),
        "reforcos_no_orcamento": decimal_to_float(registro.creditos_adicionais),
        "orcamento_atualizado": decimal_to_float(registro.dotacao_atualizada),
        "valor_comprometido": decimal_to_float(registro.valor_empenhado),
        "valor_confirmado": decimal_to_float(registro.valor_liquidado),
        "valor_pago": decimal_to_float(registro.valor_pago),
        "valor_cancelado": decimal_to_float(registro.valor_anulado),
    }


def project_planejamento_fields(
    registro: PlanejamentoDespesa,
    campos: list[str],
) -> dict[str, Any]:
    return project_public_fields(
        registro,
        campos,
        serializer=serializar_planejamento,
        order="requested",
    )
