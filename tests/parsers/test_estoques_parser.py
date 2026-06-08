from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ingestion.parsers.xml.estoques_parser import EstoquesParser


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def test_estoques_parser_parseia_materiais_com_e_sem_movimentacoes() -> None:
    registros = EstoquesParser().parse(str(FIXTURES_DIR / "estoques_sample.xml"))

    assert len(registros) == 2

    alcool = registros[0]
    assert alcool["material"] == "ALCOOL 70"
    assert alcool["unidade_medida"] == "frasco"
    assert alcool["saldo_quantidade"] == Decimal("12.0000")
    assert alcool["movimentacoes"] == []

    luva = registros[1]
    assert luva["origem"] == "prefeitura"
    assert luva["entrada_valor"] == Decimal("300.0000")
    assert len(luva["movimentacoes"]) == 3
    assert luva["movimentacoes"][0]["tipo_movimento"] == "Nota Fiscal de Compra"
    assert luva["movimentacoes"][1]["valor_total"] == Decimal("-8.0000")
    assert luva["movimentacoes"][2]["tipo_movimento"] == "Aplicacao Imediata"


def test_estoques_parser_ignora_arquivo_vazio_com_raiz_estoque(tmp_path) -> None:
    arquivo = tmp_path / "estoque-vazio.xml"
    arquivo.write_text(
        '<?xml version="1.0" encoding="ISO-8859-1"?><ESTOQUE/>',
        encoding="utf-8",
    )

    assert EstoquesParser().parse(str(arquivo)) == []


def test_estoques_parser_rejeita_layout_nao_suportado() -> None:
    with pytest.raises(ValueError, match="raiz ESTOQUE"):
        EstoquesParser().parse(str(FIXTURES_DIR / "estoques_invalid_layout.xml"))
