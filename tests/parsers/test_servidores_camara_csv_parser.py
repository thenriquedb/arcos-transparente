from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ingestion.parsers.csv.servidores_camara_parser import ServidoresCamaraCsvParser


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "servidores_camara_sample.csv"
INVALID_HEADER = Path(__file__).resolve().parents[1] / "fixtures" / "servidores_camara_invalid_header.csv"


def test_parser_extrai_competencia_e_registros() -> None:
    parser = ServidoresCamaraCsvParser()
    registros = parser.parse(str(FIXTURE))

    assert len(registros) == 3

    primeiro = registros[0]
    assert primeiro["competencia_referencia"] == date(2026, 1, 1)
    assert primeiro["matricula"] == "1600/1"
    assert primeiro["nome"] == "Virginia Oliveira de Sousa"
    assert primeiro["cargo"] == "ADVOGADO"
    assert primeiro["lotacao"] == "Secretaria da Camara"
    assert primeiro["situacao_funcional"] == "Em atividade"
    assert primeiro["data_admissao"] == date(2016, 4, 27)
    assert float(primeiro["salario_base"]) == pytest.approx(6181.74)
    assert float(primeiro["proventos"]) == pytest.approx(8530.79)
    assert float(primeiro["vantagens"]) == pytest.approx(0.00)
    assert float(primeiro["proventos_totais"]) == pytest.approx(8530.79)
    assert float(primeiro["descontos"]) == pytest.approx(2035.61)
    assert float(primeiro["liquido"]) == pytest.approx(6495.18)


def test_parser_mapeia_situacao_cedencia() -> None:
    parser = ServidoresCamaraCsvParser()
    registros = parser.parse(str(FIXTURE))

    cedido = next(r for r in registros if r["matricula"] == "2143/1")
    assert cedido["situacao_funcional"] == "Cedência"


def test_parser_rejeita_arquivo_sem_cabecalho(tmp_path) -> None:
    parser = ServidoresCamaraCsvParser()
    arquivo = tmp_path / "sem_cabecalho.csv"
    arquivo.write_text("Titulo - 2026/01\ndados;sem;cabecalho\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Cabecalho"):
        parser.parse(str(arquivo))


def test_parser_rejeita_arquivo_sem_competencia(tmp_path) -> None:
    parser = ServidoresCamaraCsvParser()
    arquivo = tmp_path / "sem_competencia.csv"
    arquivo.write_text(
        "Titulo sem data\nNome; Matrícula; Cargo; Lotação; Vínculo; Situação; Admissão; Salário Base; Proventos; Vantagens; Proventos Totais; Descontos; Líquido\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Competencia"):
        parser.parse(str(arquivo))
