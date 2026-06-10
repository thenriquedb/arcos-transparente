from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ingestion.parsers.csv.diarias_parser import DiariasCsvParser


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_diarias_csv_parser_parseia_linhas_com_metadata_e_valores() -> None:
    registros = DiariasCsvParser().parse(str(FIXTURES_DIR / "diarias_camara_sample.csv"))

    assert len(registros) == 2
    assert registros[0]["tipo_origem"] == "diaria"
    assert registros[0]["origem"] == "camara"
    assert registros[0]["exercicio"] == 2025
    assert registros[0]["data_documento"] == date(2025, 12, 31)
    assert registros[0]["periodo_referencia_inicio"] == date(2025, 1, 1)
    assert registros[0]["periodo_referencia_fim"] == date(2025, 12, 31)
    assert registros[0]["credor"] == "ALEX GRACIERES RIBEIRO"
    assert registros[0]["valor_empenhado"] == Decimal("4128.00")
    assert registros[0]["valor_liquidado"] == Decimal("4128.00")
    assert registros[0]["valor_pago"] == Decimal("4128.00")
    assert registros[0]["categoria_documento"] == "DIARIAS"
    assert registros[0]["descricao_acao"] == "Diarias/Passagens/Adiantamento de Viagem"
    assert registros[1]["sequencia_origem"] == 2
    assert registros[1]["numero_documento"] == "DIARIA-2025-00002"


def test_diarias_csv_parser_falha_quando_cabecalho_nao_e_suportado() -> None:
    with pytest.raises(ValueError, match="Cabecalho de diarias CSV nao encontrado"):
        DiariasCsvParser().parse(str(FIXTURES_DIR / "diarias_invalid_header.csv"))
