from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ingestion.schemas.contratos import ContratoInSchema


def _payload_base() -> dict[str, str]:
    return {
        "numero": "001/2025",
        "numero_licitatorio": "123/2025",
        "numero_instrumento": "001/2025",
        "tipo_instrumento_contratual": "Contrato",
        "fornecedor": "Fornecedor Alfa",
        "cnpj": "12.345.678/0001-99",
        "valor": "R$ 10.500,00",
        "data_inicio": "10/01/2025",
        "data_fim": "2026-01-10",
        "categoria": "Prestacao de Servico",
        "secretaria": "Secretaria de Saude",
        "possui_aditivo": "Nao",
        "descricao": "Locacao de estrutura",
    }


def test_schema_contrato_converte_dados_e_aplica_defaults() -> None:
    payload = _payload_base()
    payload["categoria"] = "   "
    payload["secretaria"] = None
    payload["descricao_despesa"] = "  Festividades e Homenagens  "
    payload["xml_original"] = (
        "  <InstrumentoContratual><Objeto>Locacao</Objeto></InstrumentoContratual>  "
    )
    payload["despesas_orcamentarias"] = [
        {
            "unidade_gestora": "Secretaria de Saude",
            "exercicio": "2025",
            "descricao_despesa": "Festividades e Homenagens",
            "valor_despesa": "R$ 7.500,00",
        }
    ]
    payload["itens_adquiridos"] = [
        {
            "numero_lote": "1",
            "numero_item": "2",
            "identificacao": "Estrutura de evento",
            "quantidade": "2.0000",
            "valor_total": "R$ 10.500,00",
        }
    ]

    schema = ContratoInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert data["valor"] == Decimal("10500.00")
    assert data["data_inicio"] == date(2025, 1, 10)
    assert data["data_fim"] == date(2026, 1, 10)
    assert data["categoria"] == "nao_informado"
    assert data["secretaria"] == "nao_informado"
    assert data["descricao_despesa"] == "Festividades e Homenagens"
    assert (
        data["xml_original"]
        == "<InstrumentoContratual><Objeto>Locacao</Objeto></InstrumentoContratual>"
    )
    assert data["despesas_orcamentarias"][0]["exercicio"] == 2025
    assert data["despesas_orcamentarias"][0]["valor_despesa"] == Decimal("7500.00")
    assert data["itens_adquiridos"][0]["quantidade"] == Decimal("2.0000")


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


def test_schema_contrato_descarta_filhos_invalidos_e_mantem_pai() -> None:
    payload = _payload_base()
    payload["despesas_orcamentarias"] = [
        {
            "unidade_gestora": "Secretaria de Saude",
            "exercicio": "2025",
            "descricao_despesa": "Valida",
            "valor_despesa": "R$ 7.500,00",
        },
        {
            "unidade_gestora": "Secretaria de Saude",
            "exercicio": "abc",
            "descricao_despesa": "Invalida",
            "valor_despesa": "R$ 1,00",
        },
    ]
    payload["itens_adquiridos"] = [
        {
            "numero_lote": "1",
            "identificacao": "Item valido",
            "quantidade": "2",
            "valor_total": "R$ 10,00",
        },
        {
            "numero_lote": "2",
            "identificacao": "Item invalido",
            "quantidade": "abc",
            "valor_total": "R$ 5,00",
        },
    ]

    schema = ContratoInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert len(data["despesas_orcamentarias"]) == 1
    assert data["despesas_orcamentarias"][0]["exercicio"] == 2025
    assert len(data["itens_adquiridos"]) == 1
    assert data["itens_adquiridos"][0]["identificacao"] == "Item valido"
