from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from ingestion.parsers.xml.contratos_parser import ContratosParser


def test_parser_contratos_filtra_invalidos_sem_quebrar_lote() -> None:
    parser = ContratosParser()
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "contratos_sample.xml"
    )

    registros = parser.parse(str(fixture_path))

    assert len(registros) == 2

    primeiro = registros[0]
    assert primeiro["numero"] == "001/2025"
    assert primeiro["valor"] == Decimal("10500.00")
    assert primeiro["data_inicio"] == date(2025, 1, 10)
    assert primeiro["data_fim"] == date(2026, 1, 10)
    assert primeiro["descricao_despesa"] == "Festividades e Homenagens"

    segundo = registros[1]
    assert segundo["numero"] == "003/2025"
    assert segundo["categoria"] == "nao_informado"
    assert segundo["secretaria"] == "nao_informado"
    assert segundo["data_inicio"] == date(2025, 2, 15)
    assert segundo["descricao_despesa"] == "Outros Materiais de Consumo"
