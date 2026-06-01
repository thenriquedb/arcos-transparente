from __future__ import annotations

from decimal import Decimal

from ingestion.parsers.xml.frotas_parser import FrotasParser


def test_frotas_parser_parseia_iso_8859_1_e_sanitiza_controles_invalidos(
    tmp_path,
) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Frota>
    <Frotas>
        <CodigoVeiculo>CAR-001</CodigoVeiculo>
        <PlacaVeiculo>HJK1234</PlacaVeiculo>
        <DescricaoMaterial>CAMINHÃO\x00 BASCULANTE</DescricaoMaterial>
        <DescricaoUnidadeGestora>SECRETARIA DE OBRAS</DescricaoUnidadeGestora>
        <Marca>VOLKSWAGEN</Marca>
        <Modelo>15.190</Modelo>
        <dataAquisicao>2025-01-15T00:00:00</dataAquisicao>
        <AnoFabricacao>2024</AnoFabricacao>
        <MarcadorAtual>12.345,67</MarcadorAtual>
        <Fornecedor>Mecânica São José</Fornecedor>
        <ValorAtual>89.000,50</ValorAtual>
        <FrotasDespesas>
            <FrotasDespesas>
                <DescricaoEvento>Troca de óleo\x1f</DescricaoEvento>
                <QuantidadeLancamento>1,00</QuantidadeLancamento>
                <ValorLancamento>350,00</ValorLancamento>
                <DataEvento>20/02/2025</DataEvento>
                <TipoDespesa>Manutenção</TipoDespesa>
                <TotalDespesa>350,00</TotalDespesa>
            </FrotasDespesas>
        </FrotasDespesas>
    </Frotas>
</Frota>
"""
    arquivo = tmp_path / "frota-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = FrotasParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["descricao_material"] == "CAMINHÃO BASCULANTE"
    assert registros[0]["fornecedor"] == "Mecânica São José"
    assert registros[0]["marcador_atual"] == Decimal("12345.67")
    assert registros[0]["valor_atual"] == Decimal("89000.50")
    assert registros[0]["despesas"][0]["descricao_evento"] == "Troca de óleo"
