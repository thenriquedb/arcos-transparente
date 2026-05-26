from __future__ import annotations

from decimal import Decimal

from ingestion.parsers.xml.patrimonios_parser import PatrimoniosParser


def test_patrimonios_parser_parseia_bem_e_gera_placa_fallback(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Patrimonios>
    <ITEM>
        <UnidadeGestora>PREFEITURA MUNICIPAL</UnidadeGestora>
        <PLACA>27982</PLACA>
        <SITUACAOBEM>Patrimonial</SITUACAOBEM>
        <CLASSIFICACAO>006115</CLASSIFICACAO>
        <DESCRICAOITEM>REFRIGERADOR DOMÉSTICO</DESCRICAOITEM>
        <TIPOINGRESSO>Compra</TIPOINGRESSO>
        <DATAAQUISICAO>07/03/2025</DATAAQUISICAO>
        <LOCALIZACAO>L005 - SEC. MUNIC. DE EDUCAÇÃO</LOCALIZACAO>
        <STATUS>Normal</STATUS>
        <VALORINGRESSO>1995.0000</VALORINGRESSO>
        <VALORATUALIZADO>1995.0000</VALORATUALIZADO>
    </ITEM>
    <ITEM>
        <UnidadeGestora>PREFEITURA MUNICIPAL</UnidadeGestora>
        <DESCRICAOITEM>ITEM SEM PLACA</DESCRICAOITEM>
        <VALORATUALIZADO>100.0000</VALORATUALIZADO>
    </ITEM>
</Patrimonios>
"""
    arquivo = tmp_path / "patrimonio-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = PatrimoniosParser().parse(str(arquivo))

    assert len(registros) == 2
    assert registros[0]["placa"] == "27982"
    assert registros[0]["valor_atualizado"] == Decimal("1995.0000")
    assert registros[1]["placa"] == "sem_placa_00002"
