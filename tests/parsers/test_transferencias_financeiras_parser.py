from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ingestion.parsers.xml.transferencias_financeiras_parser import (
    TransferenciasFinanceirasParser,
)


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_transferencias_financeiras_parser_parseia_movimentos_xml() -> None:
    registros = TransferenciasFinanceirasParser().parse(
        str(FIXTURES_DIR / "transferencias_financeiras_sample.xml")
    )

    assert len(registros) == 2
    assert registros[0]["arquivo_origem"] == "transferencias_financeiras_sample.xml"
    assert registros[0]["sequencia_origem"] == 1
    assert registros[0]["exercicio"] == 2026
    assert registros[0]["identificacao"] == "27"
    assert registros[0]["unidade_gestora_concessora"] == "PREFEITURA MUNICIPAL"
    assert registros[0]["unidade_gestora_recebedora"] == "CAMARA MUNICIPAL"
    assert registros[0]["data_movimento"] == "2026-01-01"
    assert registros[0]["tipo_movimento"] == "Programacao Inicial"
    assert registros[0]["programacao_inicial"] == Decimal("6630000.00")
    assert registros[0]["valor_movimento"] == Decimal("6630000.00")
    assert registros[1]["data_movimento"] == "2026-01-16"
    assert registros[1]["tipo_movimento"] == "Recebimento"
