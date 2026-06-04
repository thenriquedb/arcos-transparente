from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from ingestion.schemas.servidores import ServidorInSchema


def _payload_base() -> dict[str, str]:
    return {
        "source_id": "101",
        "competencia_referencia": "01/2026",
        "nome": "Maria da Silva",
        "cpf": "***345.678-**",
        "matricula": "90001-1",
        "cargo_funcao": "Enfermeira",
        "fundamento_legal": " ",
        "lotacao": "UPA Central",
        "situacao_funcional": "Em atividade",
        "forma_contratacao_investidura": "Processo Seletivo",
        "data_admissao": "02/01/2025",
        "data_desligamento": "          ",
        "horario_trabalho": "12:00 as 18:00",
        "carga_horaria": "",
        "local_origem_cedencia": "",
        "local_destino_cedencia": "",
        "onus_pagamento_cedencia": "",
        "data_inicio_cessao": "          ",
        "data_fim_cessao": "          ",
        "regime_aposentadoria": "Geral",
        "vinculo_empregaticio": "Temporario",
    }


def test_schema_servidor_json_converte_campos_e_limpa_vazios() -> None:
    payload = _payload_base()
    payload["fundamento_legal"] = "   "
    payload["data_fim_cessao"] = "31/12/2025"

    schema = ServidorInSchema.model_validate(payload)
    data = schema.model_dump(mode="python")

    assert data["source_id"] == 101
    assert data["fundamento_legal"] is None
    assert data["competencia_referencia"] == date(2026, 1, 1)
    assert data["data_admissao"] == date(2025, 1, 2)
    assert data["data_desligamento"] is None
    assert data["carga_horaria"] is None
    assert data["data_fim_cessao"] == date(2025, 12, 31)


def test_schema_servidor_json_rejeita_obrigatorios_ausentes() -> None:
    payload = _payload_base()
    payload.pop("nome")

    with pytest.raises(ValidationError):
        ServidorInSchema.model_validate(payload)


def test_schema_servidor_json_rejeita_competencia_invalida() -> None:
    payload = _payload_base()
    payload["competencia_referencia"] = "13/2026"

    with pytest.raises(ValidationError):
        ServidorInSchema.model_validate(payload)


def test_schema_servidor_json_rejeita_source_id_invalido() -> None:
    payload = _payload_base()
    payload["source_id"] = "0"

    with pytest.raises(ValidationError):
        ServidorInSchema.model_validate(payload)
