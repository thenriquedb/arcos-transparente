from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ingestion.parsers.csv.passagens_parser import PassagensCsvParser


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_passagens_csv_parser_parseia_linhas_com_metadata_e_valores() -> None:
    registros = PassagensCsvParser().parse(str(FIXTURES_DIR / "passagens_camara_sample.csv"))

    assert len(registros) == 2
    assert registros[0]["tipo_origem"] == "passagem"
    assert registros[0]["origem"] == "camara"
    assert registros[0]["exercicio"] == 2026
    assert registros[0]["data_documento"] == date(2026, 6, 30)
    assert registros[0]["periodo_referencia_inicio"] == date(2026, 1, 1)
    assert registros[0]["periodo_referencia_fim"] == date(2026, 6, 30)
    assert registros[0]["credor"] == "EDISON DOS SANTOS"
    assert registros[0]["categoria_documento"] == "PASSAGENS E DESPESAS COM LOCOMOCAO"
    assert registros[0]["descricao_acao"] == "Diarias/Passagens/Adiantamento de Viagem"
    assert registros[0]["valor_empenhado"] == Decimal("2000.00")
    assert registros[0]["valor_liquidado"] == Decimal("1500.09")
    assert registros[0]["valor_pago"] == Decimal("1500.09")
    assert registros[1]["sequencia_origem"] == 2
    assert registros[1]["numero_documento"] == "PASSAGEM-2026-00002"


def test_passagens_csv_parser_falha_quando_cabecalho_nao_e_suportado() -> None:
    with pytest.raises(ValueError, match="Cabecalho de passagens CSV nao encontrado"):
        PassagensCsvParser().parse(str(FIXTURES_DIR / "passagens_invalid_header.csv"))
