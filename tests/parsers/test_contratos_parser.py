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
    assert primeiro["numero_licitatorio"] == "123/2025"
    assert primeiro["numero_instrumento"] == "001/2025"
    assert primeiro["tipo_instrumento_contratual"] == "Contrato"
    assert primeiro["valor"] == Decimal("10500.00")
    assert primeiro["data_inicio"] == date(2025, 1, 10)
    assert primeiro["data_fim"] == date(2026, 1, 10)
    assert primeiro["possui_aditivo"] == "Nao"
    assert primeiro["descricao_despesa"] == "Festividades e Homenagens"
    assert "<InstrumentoContratual>" in primeiro["xml_original"]
    assert (
        "<DescricaoDespesa>Festividades e Homenagens</DescricaoDespesa>"
        in primeiro["xml_original"]
    )
    assert len(primeiro["despesas_orcamentarias"]) == 2
    assert (
        primeiro["despesas_orcamentarias"][0]["natureza_despesa_rubrica"]
        == "339039200000"
    )
    assert primeiro["despesas_orcamentarias"][0]["valor_despesa"] == Decimal("7500.00")
    assert primeiro["itens_adquiridos"][0]["numero_item"] == "2"
    assert primeiro["itens_adquiridos"][0]["valor_total"] == Decimal("10500.00")

    segundo = registros[1]
    assert segundo["numero"] == "003/2025"
    assert segundo["numero_licitatorio"] == "003/2025"
    assert segundo["numero_instrumento"] is None
    assert segundo["tipo_instrumento_contratual"] == "Ata"
    assert segundo["categoria"] == "nao_informado"
    assert segundo["secretaria"] == "nao_informado"
    assert segundo["data_inicio"] == date(2025, 2, 15)
    assert segundo["descricao_despesa"] == "Outros Materiais de Consumo"
    assert segundo["itens_adquiridos"][0]["numero_lote"] == "3"


def test_parser_contratos_sanitiza_xml_original_e_campos_textuais(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<Root>
    <InstrumentoContratual>
        <NumeroLicitatorio>321/2025</NumeroLicitatorio>
        <NumeroInstrumentoContratual>009/2025</NumeroInstrumentoContratual>
        <TipoInstrumentoContratual>Contrato</TipoInstrumentoContratual>
        <NomeFornecedor>Fornecedor\x00 Limpo</NomeFornecedor>
        <CNPJFornecedor>12.345.678/0001-99</CNPJFornecedor>
        <ValorInstrumentoContratual>R$ 1.200,00</ValorInstrumentoContratual>
        <DataEmissao>10/01/2025</DataEmissao>
        <TipoContrato>Prestação\x1f de Serviço</TipoContrato>
        <UnidadeGestora>Secretaria de Saúde</UnidadeGestora>
        <Objeto>Locação\x00 de palco</Objeto>
        <DespesasOrcamentarias>
            <DespesaOrcamentaria>
                <DescricaoDespesa>Eventos\x1f Oficiais</DescricaoDespesa>
            </DespesaOrcamentaria>
        </DespesasOrcamentarias>
    </InstrumentoContratual>
</Root>
"""
    arquivo = tmp_path / "contratos-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = ContratosParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["fornecedor"] == "Fornecedor Limpo"
    assert registros[0]["categoria"] == "Prestação de Serviço"
    assert registros[0]["descricao"] == "Locação de palco"
    assert registros[0]["descricao_despesa"] == "Eventos Oficiais"
    assert "\x00" not in registros[0]["xml_original"]
    assert "\x1f" not in registros[0]["xml_original"]
