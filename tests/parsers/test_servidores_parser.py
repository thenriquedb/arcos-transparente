from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from ingestion.parsers.xml.servidores_parser import ServidoresParser


def test_parser_servidores_filtra_invalidos_sem_quebrar_lote() -> None:
    parser = ServidoresParser()
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "servidores_sample.xml"
    )

    registros = parser.parse(str(fixture_path))

    assert len(registros) == 2

    primeiro = registros[0]
    assert primeiro["nome"] == "Maria da Silva"
    assert primeiro["cargo"] == "Enfermeira"
    assert primeiro["secretaria"] == "nao_informado"
    assert primeiro["salario_base"] == Decimal("2345.67")
    assert primeiro["competencia_referencia"] == date(2025, 1, 1)

    segundo = registros[1]
    assert segundo["nome"] == "Carlos Pereira"
    assert segundo["competencia_referencia"] == date(2025, 4, 1)
