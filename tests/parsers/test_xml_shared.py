from __future__ import annotations

from ingestion.parsers.xml.shared import (
    parse_xml_root,
    read_xml_text,
    sanitize_xml_payload,
    sanitize_xml_text,
)


def test_read_xml_text_decodifica_iso_8859_1_e_remove_controles_invalidos(
    tmp_path,
) -> None:
    xml = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        "<Root><Descricao>Atenção Básica\x00</Descricao></Root>"
    )
    arquivo = tmp_path / "amostra.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    conteudo = read_xml_text(arquivo)

    assert "Atenção Básica" in conteudo
    assert "\x00" not in conteudo


def test_parse_xml_root_preserva_acentos_e_ignora_controles_invalidos(tmp_path) -> None:
    xml = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        "<Root><Nome>Educação\x1f Infantil</Nome></Root>"
    )
    arquivo = tmp_path / "raiz.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    root = parse_xml_root(arquivo)

    assert root.findtext("./Nome") == "Educação Infantil"


def test_sanitize_xml_payload_sanitiza_strings_aninhadas_sem_perder_whitespace() -> (
    None
):
    payload = {
        "descricao": "Linha 1\x00\nLinha 2",
        "filhos": [
            {"nome": "Tab\tok\x1f"},
            ("A\x00B",),
        ],
    }

    sanitized = sanitize_xml_payload(payload)

    assert sanitized["descricao"] == "Linha 1\nLinha 2"
    assert sanitized["filhos"][0]["nome"] == "Tab\tok"
    assert sanitized["filhos"][1][0] == "AB"
    assert sanitize_xml_text(None) is None
