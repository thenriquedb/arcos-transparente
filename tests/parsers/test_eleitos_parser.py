from __future__ import annotations

from ingestion.parsers.xml.eleitos_parser import EleitosParser


def test_eleitos_parser_parseia_vereadores_e_prefeitos_por_mandato(tmp_path) -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<transparencia>
    <vereadores municipio="Arcos" estado="MG">
        <vereador id="1">
            <nomeCompleto>Maria Silva</nomeCompleto>
            <partido>PL</partido>
            <mandatos>
                <mandato>
                    <inicio>2025</inicio>
                    <fim>2028</fim>
                    <status>em exercício</status>
                </mandato>
            </mandatos>
        </vereador>
    </vereadores>
    <prefeitos municipio="Arcos" estado="MG">
        <prefeito id="2">
            <nomeCompleto>Joao Souza</nomeCompleto>
            <mandatos>
                <mandato>
                    <inicio>2021</inicio>
                    <fim>2024</fim>
                    <status>encerrado</status>
                </mandato>
                <mandato>
                    <inicio>2025</inicio>
                    <fim>2028</fim>
                    <status>em exercício</status>
                </mandato>
            </mandatos>
        </prefeito>
    </prefeitos>
</transparencia>
"""
    arquivo = tmp_path / "eleitos.xml"
    arquivo.write_text(xml, encoding="utf-8")

    registros = EleitosParser().parse(str(arquivo))

    assert len(registros) == 3
    assert registros[0]["tipo_politico"] == "vereador"
    assert registros[0]["nome_completo"] == "Maria Silva"
    assert registros[0]["mandato_inicio"] == 2025
    assert registros[0]["mandato_status"] == "em exercício"
    assert registros[1]["tipo_politico"] == "prefeito"
    assert registros[1]["mandato_inicio"] == 2021
    assert registros[2]["mandato_fim"] == 2028
