from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ingestion.schemas.contratos import ContratoInSchema


def _payload_base() -> dict[str, str]:
    return {
        "numero": "001/2025",
        "fornecedor": "Fornecedor Alfa",
        "cnpj": "12.345.678/0001-99",
        "valor": "R$ 10.500,00",
        "data_inicio": "10/01/2025",
        "data_fim": "2026-01-10",
        "categoria": "Prestacao de Servico",
        "secretaria": "Secretaria de Saude",
        "descricao": "Locacao de estrutura",
    }


def test_schema_contrato_converte_dados_e_aplica_defaults() -> None:
    payload = _payload_base()
    payload["categoria"] = "   "
    payload["secretaria"] = None
    payload["descricao_despesa"] = "  Festividades e Homenagens  "

    schema = ContratoInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert data["valor"] == Decimal("10500.00")
    assert data["data_inicio"] == date(2025, 1, 10)
    assert data["data_fim"] == date(2026, 1, 10)
    assert data["categoria"] == "nao_informado"
    assert data["secretaria"] == "nao_informado"
    assert data["descricao_despesa"] == "Festividades e Homenagens"


def test_schema_contrato_rejeita_obrigatorios_ausentes() -> None:
    payload = _payload_base()
    payload.pop("numero")

    with pytest.raises(ValidationError):
        ContratoInSchema.model_validate(payload)


def test_schema_contrato_rejeita_data_invalida() -> None:
    payload = _payload_base()
    payload["data_inicio"] = "99/99/2025"

    with pytest.raises(ValidationError):
        ContratoInSchema.model_validate(payload)
