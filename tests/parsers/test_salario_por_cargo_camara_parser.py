from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ingestion.parsers.csv.salario_por_cargo_camara_parser import SalarioPorCargoCamaraParser


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "salario_por_cargo_camara_sample.csv"


def test_parser_extrai_competencia_e_cargos() -> None:
    parser = SalarioPorCargoCamaraParser()
    registros = parser.parse(str(FIXTURE))

    assert len(registros) == 3

    primeiro = registros[0]
    assert primeiro["competencia_referencia"] == date(2026, 1, 1)
    assert primeiro["codigo"] == "22"
    assert primeiro["descricao"] == "ADVOGADO"

    terceiro = registros[2]
    assert terceiro["codigo"] == "1"
    assert terceiro["descricao"] == "Vereador"


def test_parser_ignora_rodape_pronim() -> None:
    parser = SalarioPorCargoCamaraParser()
    registros = parser.parse(str(FIXTURE))

    descricoes = [r["descricao"] for r in registros]
    assert not any("PRONIM" in d for d in descricoes)


def test_parser_rejeita_arquivo_sem_mes(tmp_path) -> None:
    parser = SalarioPorCargoCamaraParser()
    arquivo = tmp_path / "sem_mes.csv"
    arquivo.write_text(
        '="Filtros Utilizados"\n="Código";="Descrição do Cargo"\n="1";="Vereador"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Competencia"):
        parser.parse(str(arquivo))
