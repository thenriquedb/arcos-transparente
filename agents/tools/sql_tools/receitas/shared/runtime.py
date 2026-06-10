"""Serializacao publica das tools de receitas."""

from __future__ import annotations

from typing import Any

from database.models import ReceitaArrecadacao, ReceitaLancamento
from agents.tools.sql_tools.shared.projection import project_public_dict
from shared.utils.decimal_to_float import decimal_to_float
from shared.utils.validation import parse_month


def serializar_receita_arrecadacao(registro: ReceitaArrecadacao) -> dict[str, Any]:
    return {
        "id": registro.id,
        "tipo_de_dado": "arrecadacao",
        "ano": registro.exercicio,
        "mes": registro.mes,
        "mes_num": parse_month(registro.mes),
        "data": registro.data_arrecadacao,
        "unidade_responsavel": registro.unidade_gestora,
        "categoria_codigo": registro.natureza.identificacao if registro.natureza else None,
        "categoria": registro.natureza.nome if registro.natureza else None,
        "tipo": None,
        "tributo": None,
        "origem_do_recurso": registro.fonte_recurso,
        "valor_previsto": decimal_to_float(registro.valor_previsto_liquido),
        "valor_recebido": decimal_to_float(registro.valor_arrecadado_liquido),
        "valor_previsto_bruto": decimal_to_float(registro.valor_previsto_bruto),
        "valor_recebido_bruto": decimal_to_float(registro.valor_arrecadado_bruto),
        "descontos_previstos": decimal_to_float(registro.valor_previsto_deducoes),
        "descontos_realizados": decimal_to_float(registro.valor_realizado_deducoes),
        "valor_lancado": None,
        "valor_em_divida_ativa": None,
        "valor_em_cobranca_judicial": None,
    }


def serializar_receita_lancamento(registro: ReceitaLancamento) -> dict[str, Any]:
    return {
        "id": registro.id,
        "tipo_de_dado": "lancamento",
        "ano": registro.exercicio,
        "mes": registro.mes,
        "mes_num": parse_month(registro.mes),
        "data": registro.data_lancamento,
        "unidade_responsavel": None,
        "categoria_codigo": None,
        "categoria": None,
        "tipo": registro.tipo_receita,
        "tributo": registro.tributo,
        "origem_do_recurso": None,
        "valor_previsto": None,
        "valor_recebido": None,
        "valor_previsto_bruto": None,
        "valor_recebido_bruto": None,
        "descontos_previstos": None,
        "descontos_realizados": None,
        "valor_lancado": decimal_to_float(registro.valor_lancado_exercicio),
        "valor_em_divida_ativa": decimal_to_float(registro.valor_lancado_divida_ativa),
        "valor_em_cobranca_judicial": decimal_to_float(registro.valor_lancado_cobraca_judicial),
    }


def project_receita_fields(registro: dict[str, Any], campos: list[str]) -> dict[str, Any]:
    """Projeta o registro nos campos publicos solicitados."""

    return project_public_dict(registro, campos, order="requested")
