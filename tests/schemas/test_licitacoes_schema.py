from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ingestion.schemas.licitacoes import LicitacaoInSchema


def _payload_base() -> dict:
    return {
        "numero": "100/2025",
        "modalidade": "Pregao Eletronico",
        "objeto": "Compra de equipamentos",
        "valor_estimado": "R$ 1.234,56",
        "data_abertura": "07/02/2025",
        "vencedores": [],
        "instrumentos_contratuais": [],
    }


def test_schema_converte_dados_e_aplica_defaults() -> None:
    payload = _payload_base()
    payload["situacao"] = "   "
    payload["secretaria"] = None
    payload["instrumentos_contratuais"] = [
        {
            "numero_instrumento": "A-1",
            "data_emissao": "2025-03-10",
            "data_expiracao": "10/03/2026",
            "valor_instrumento_contratual": "R$ 200,00",
            "materias": [
                {
                    "identificacao": "Item 1",
                    "quantidade": "2,50",
                    "valor_unitario": "R$ 50,00",
                    "valor_total": "R$ 125,00",
                }
            ],
        }
    ]

    schema = LicitacaoInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert isinstance(data["data_abertura"], date)
    assert data["data_abertura"] == date(2025, 2, 7)
    assert data["valor_estimado"] == Decimal("1234.56")
    assert data["situacao"] == "nao_informado"
    assert data["secretaria"] == "nao_informado"
    assert data["instrumentos_contratuais"][0]["data_emissao"] == date(2025, 3, 10)
    assert data["instrumentos_contratuais"][0]["materias"][0]["quantidade"] == Decimal(
        "2.50"
    )


def test_schema_rejeita_campos_obrigatorios_ausentes() -> None:
    payload = _payload_base()
    payload.pop("numero")

    with pytest.raises(ValidationError):
        LicitacaoInSchema.model_validate(payload)


def test_schema_descarta_filhos_invalidos_e_mantem_pai() -> None:
    payload = _payload_base()
    payload["vencedores"] = [
        {"cnpj_cpf": "123", "nome": "Fornecedor Valido"},
        {"cnpj_cpf": "456", "nome": "   "},
    ]
    payload["instrumentos_contratuais"] = [
        {
            "numero_instrumento": "OK-1",
            "data_emissao": "2025-03-15",
            "materias": [
                {
                    "identificacao": "Material valido",
                    "quantidade": "1,00",
                    "valor_unitario": "R$ 10,00",
                    "valor_total": "R$ 10,00",
                },
                {
                    "identificacao": "Material invalido",
                    "quantidade": "abc",
                    "valor_unitario": "R$ 20,00",
                    "valor_total": "R$ 20,00",
                },
            ],
        },
        {
            "numero_instrumento": "INV-1",
            "data_emissao": "99/99/2025",
        },
    ]

    schema = LicitacaoInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert len(data["vencedores"]) == 1
    assert data["vencedores"][0]["cnpj_cpf"] == "123"
    assert len(data["instrumentos_contratuais"]) == 1
    assert data["instrumentos_contratuais"][0]["numero_instrumento"] == "OK-1"
    assert len(data["instrumentos_contratuais"][0]["materias"]) == 1
