"""Utilitarios compartilhados de serializacao das tools de contratos."""

from __future__ import annotations

from typing import Any

from database.models import (
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
)
from shared.utils.decimal_to_float import decimal_to_float

from .responses import (
    ContratoDespesaOrcamentariaToolItem,
    ContratoItemAdquiridoToolItem,
    ContratoToolItem,
)


def serializar_contrato(contrato: Contrato) -> dict[str, Any]:
    """Serializa o modelo ORM em payload padronizado para as tools."""

    payload = ContratoToolItem.model_validate(
        {
            "id": contrato.id,
            "numero": contrato.numero,
            "fornecedor": contrato.fornecedor,
            "documento_fornecedor": contrato.cnpj,
            "valor": decimal_to_float(contrato.valor),
            "data_inicio": contrato.data_inicio,
            "data_fim": contrato.data_fim,
            "categoria": contrato.categoria,
            "secretaria": contrato.secretaria,
            "descricao": contrato.descricao,
            "classificacao_da_despesa": contrato.descricao_despesa,
        }
    )
    return payload.model_dump(mode="json")


def serializar_contrato_despesa(
    despesa: ContratoDespesaOrcamentaria,
) -> dict[str, Any]:
    payload = ContratoDespesaOrcamentariaToolItem.model_validate(
        {
            "ordem": despesa.ordem,
            "unidade_gestora": despesa.unidade_gestora,
            "exercicio": despesa.exercicio,
            "orgao": despesa.orgao,
            "unidade": despesa.unidade,
            "departamento": despesa.departamento,
            "fonte_recurso": despesa.fonte_recurso,
            "natureza_despesa_rubrica": despesa.natureza_despesa_rubrica,
            "classificacao_da_despesa": despesa.descricao_despesa,
            "valor_despesa": decimal_to_float(despesa.valor_despesa),
        }
    )
    return payload.model_dump(mode="json", exclude_none=True)


def serializar_contrato_item(item: ContratoItemAdquirido) -> dict[str, Any]:
    payload = ContratoItemAdquiridoToolItem.model_validate(
        {
            "ordem": item.ordem,
            "unidade_gestora": item.unidade_gestora,
            "numero_lote": item.numero_lote,
            "numero_item": item.numero_item,
            "identificacao": item.identificacao,
            "quantidade": decimal_to_float(item.quantidade),
            "valor_unitario": decimal_to_float(item.valor_unitario),
            "valor_total": decimal_to_float(item.valor_total),
        }
    )
    return payload.model_dump(mode="json", exclude_none=True)
