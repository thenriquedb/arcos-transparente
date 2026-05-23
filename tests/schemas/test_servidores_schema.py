from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ingestion.schemas.servidores import ServidorInSchema


def _payload_base() -> dict[str, str]:
    return {
        "nome": "Maria da Silva",
        "cargo": "Enfermeira",
        "secretaria": "Secretaria de Saude",
        "salario_base": "R$ 2.345,67",
        "data_admissao": "01/2025",
    }


def test_schema_servidor_converte_dados_e_aplica_defaults() -> None:
    payload = _payload_base()
    payload["cargo"] = "   "
    payload["secretaria"] = None

    schema = ServidorInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert data["cargo"] == "nao_informado"
    assert data["secretaria"] == "nao_informado"
    assert data["salario_base"] == Decimal("2345.67")
    assert data["data_admissao"] == date(2025, 1, 1)


def test_schema_servidor_rejeita_obrigatorios_ausentes() -> None:
    payload = _payload_base()
    payload.pop("nome")

    with pytest.raises(ValidationError):
        ServidorInSchema.model_validate(payload)


def test_schema_servidor_rejeita_competencia_invalida() -> None:
    payload = _payload_base()
    payload["data_admissao"] = "13/2025"

    with pytest.raises(ValidationError):
        ServidorInSchema.model_validate(payload)
