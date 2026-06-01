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


def test_parser_licitacoes_decodifica_iso_8859_1_com_acentos(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<ProcessosLicitatorios>
    <ProcessoLicitatorio>
        <NumeroProcesso>500/2025</NumeroProcesso>
        <Modalidade>Pregão</Modalidade>
        <Objeto>Reforma da Educação Básica</Objeto>
        <DataJulgamento>07/02/2025</DataJulgamento>
        <ValorProcesso>R$ 1.234,56</ValorProcesso>
        <UnidadeGestora>Secretaria de Saúde</UnidadeGestora>
        <InstrumentosContratuais>
            <InstrumentoContratual>
                <NumeroLicitatorio>500/2025</NumeroLicitatorio>
                <NumeroInstrumentoContratual>01/2025</NumeroInstrumentoContratual>
                <TipoContrato>Prestação de Serviço</TipoContrato>
                <DataEmissao>2025-02-20</DataEmissao>
                <ValorInstrumentoContratual>R$ 200,00</ValorInstrumentoContratual>
                <ItensAdquiridos>
                    <Item>
                        <Identificacao>Material pedagógico</Identificacao>
                        <Quantidade>2,00</Quantidade>
                        <ValorUnitario>R$ 100,00</ValorUnitario>
                        <ValorTotal>R$ 200,00</ValorTotal>
                    </Item>
                </ItensAdquiridos>
            </InstrumentoContratual>
        </InstrumentosContratuais>
    </ProcessoLicitatorio>
</ProcessosLicitatorios>
"""
    arquivo = tmp_path / "licitacoes-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = LicitacoesParser().parse(str(arquivo))

    assert len(registros) == 1
    assert registros[0]["objeto"] == "Reforma da Educação Básica"
    assert registros[0]["secretaria"] == "Secretaria de Saúde"
    assert (
        registros[0]["instrumentos_contratuais"][0]["materias"][0]["identificacao"]
        == "Material pedagógico"
    )
