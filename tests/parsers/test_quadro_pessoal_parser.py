from __future__ import annotations

from datetime import date

from ingestion.parsers.xml.quadro_pessoal_parser import QuadroPessoalParser


def test_quadro_pessoal_parser_parseia_xml_malformado_da_saude(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="ISO-8859-1"?>
<QuadroPessoais>
    <QuadroPessoal>
        <Competencia>01/2025</Competencia>
        <RegimeContratacao>Aposentado</RegimeContratacao>
        <VagasCriadas>15</VagasCriadas>
        <VagasPreenchidas>30</VagasPreenchidas>
    </QuadroPessoal>
    <QuadroPessoal>
        <Competencia>01/2025</Competencia>
        <RegimeContratacao>Temporario</RegimeContratacao>
        <VagasCriadas>19</VagasCriadas>
        <QuadroPessoal>
            <Competencia>02/2025</Competencia>
            <RegimeContratacao>Aposentado</RegimeContratacao>
            <VagasCriadas>15</VagasCriadas>
            <VagasPreenchidas>30</VagasPreenchidas>
        </QuadroPessoal>
</QuadroPessoais>
"""
    arquivo = tmp_path / "quadro-pessoal-saude-2025.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    registros = QuadroPessoalParser().parse(str(arquivo))

    assert len(registros) == 3
    assert registros[0]["origem"] == "saude"
    assert registros[0]["competencia_referencia"] == date(2025, 1, 1)
    assert registros[1]["regime_contratacao"] == "Temporario"
    assert registros[1]["vagas_preenchidas"] is None
