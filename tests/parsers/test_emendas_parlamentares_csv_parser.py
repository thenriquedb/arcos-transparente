from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ingestion.parsers.csv.emendas_parlamentares_parser import (
    EmendasParlamentaresCsvParser,
)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_emendas_parlamentares_csv_parser_parseia_linhas_e_cabecalhos_repetidos() -> None:
    registros = EmendasParlamentaresCsvParser().parse(str(FIXTURES_DIR / "emendas_parlamentares_sample.csv"))

    assert len(registros) == 3
    assert registros[0]["arquivo_origem"] == "emendas_parlamentares_sample.csv"
    assert registros[0]["sequencia_origem"] == 1
    assert registros[0]["exercicio_consulta"] == 2026
    assert registros[0]["ano"] == 2025
    assert registros[0]["ano_numero"] == "2025/42670003"
    assert registros[0]["autor"] == "Cleitinho"
    assert registros[0]["funcao"] == "Urbanismo"
    assert registros[0]["valor"] == Decimal("399046.98")
    assert registros[1]["ano_numero"] == "2026/39600006"
    assert registros[1]["funcao"] == "Saude"
    assert registros[2]["autor"] == "Lafayete Andrada"


def test_emendas_parlamentares_csv_parser_falha_com_cabecalho_invalido() -> None:
    with pytest.raises(
        ValueError,
        match="Cabecalho de emendas parlamentares CSV nao encontrado",
    ):
        EmendasParlamentaresCsvParser().parse(str(FIXTURES_DIR / "emendas_parlamentares_invalid_header.csv"))
