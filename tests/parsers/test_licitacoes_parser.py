from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from ingestion.parsers.xml.licitacoes_parser import LicitacoesParser


def test_parser_licitacoes_filtra_invalidos_sem_quebrar_lote() -> None:
    parser = LicitacoesParser()
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "licitacoes_sample.xml"
    )

    registros = parser.parse(str(fixture_path))

    assert len(registros) == 2

    primeiro = registros[0]
    assert primeiro["numero"] == "100/2025"
    assert primeiro["secretaria"] == "nao_informado"
    assert primeiro["valor_estimado"] == Decimal("1234.56")
    assert primeiro["data_abertura"] == date(2025, 2, 7)

    segundo = registros[1]
    assert segundo["numero"] == "300/2025"
    assert segundo["data_abertura"] == date(2025, 3, 15)
    assert len(segundo["vencedores"]) == 1
    assert len(segundo["instrumentos_contratuais"]) == 1
    assert len(segundo["instrumentos_contratuais"][0]["materias"]) == 1
