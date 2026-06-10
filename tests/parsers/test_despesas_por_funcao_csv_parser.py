from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ingestion.parsers.csv.despesas_por_funcao_parser import (
    DespesasPorFuncaoCsvParser,
)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_despesas_por_funcao_csv_parser_parseia_funcoes_e_ignora_totais() -> None:
    registros = DespesasPorFuncaoCsvParser().parse(str(FIXTURES_DIR / "despesas_por_funcao_sample.csv"))

    assert len(registros) == 2
    assert registros[0]["arquivo_origem"] == "despesas_por_funcao_sample.csv"
    assert registros[0]["linha_origem"] == 6
    assert registros[0]["origem"] == "prefeitura"
    assert registros[0]["exercicio"] == 2025
    assert registros[0]["periodo_inicio"] == date(2025, 1, 1)
    assert registros[0]["periodo_fim"] == date(2025, 12, 31)
    assert registros[0]["funcao"] == "Saude"
    assert registros[0]["dotacao_inicial"] == Decimal("62946377.71")
    assert registros[0]["creditos_adicionais"] == Decimal("23939808.94")
    assert registros[0]["dotacao_atualizada"] == Decimal("86886186.65")
    assert registros[0]["valor_empenhado"] == Decimal("82186075.50")
    assert registros[0]["valor_liquidado"] == Decimal("74785290.81")
    assert registros[0]["valor_pago"] == Decimal("73415583.84")
    assert registros[1]["funcao"] == "Educacao"
    assert all(registro["funcao"] != "Totais" for registro in registros)


def test_despesas_por_funcao_csv_parser_falha_quando_cabecalho_nao_e_suportado() -> None:
    with pytest.raises(
        ValueError,
        match="Cabecalho de despesas-por-funcao CSV nao encontrado",
    ):
        DespesasPorFuncaoCsvParser().parse(str(FIXTURES_DIR / "despesas_por_funcao_invalid_header.csv"))
