"""Utilitarios compartilhados de serializacao das tools de contratos."""

from __future__ import annotations

from typing import Any

from database.models import Contrato
from shared.utils.decimal_to_float import decimal_to_float

from .responses import ContratoToolItem


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
