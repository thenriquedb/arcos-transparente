from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ingestion.parsers.xml.servidores_parser import ServidoresParser


def test_parser_servidores_filtra_invalidos_sem_quebrar_lote() -> None:
    parser = ServidoresParser()
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "servidores_sample.json"

    registros = parser.parse(str(fixture_path))

    assert len(registros) == 2

    primeiro = registros[0]
    assert primeiro["source_id"] == 101
    assert primeiro["nome"] == "Maria da Silva"
    assert primeiro["cargo_funcao"] == "Enfermeira"
    assert primeiro["lotacao"] == "UPA Central"
    assert primeiro["fundamento_legal"] is None
    assert primeiro["competencia_referencia"] == date(2026, 1, 1)
    assert primeiro["data_admissao"] == date(2025, 1, 2)
    assert primeiro["data_desligamento"] is None

    segundo = registros[1]
    assert segundo["source_id"] == 104
    assert segundo["nome"] == "Carlos Pereira"
    assert segundo["data_admissao"] == date(2025, 4, 1)
    assert segundo["data_fim_cessao"] == date(2025, 12, 31)


def test_parser_servidores_rejeita_layout_inesperado(tmp_path) -> None:
    parser = ServidoresParser()
    arquivo = tmp_path / "servidores-invalido.json"
    arquivo.write_text('{"id": 1}', encoding="utf-8")

    with pytest.raises(ValueError, match="lista de objetos suportados"):
        parser.parse(str(arquivo))
