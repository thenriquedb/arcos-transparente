from __future__ import annotations

import pytest

from ingestion.parsers.xml.shared import (
    parse_xml_root,
    read_xml_text,
    sanitize_xml_payload,
    sanitize_xml_text,
)


def test_read_xml_text_decodifica_iso_8859_1_e_remove_controles_invalidos(
    tmp_path,
) -> None:
    xml = '<?xml version="1.0" encoding="ISO-8859-1"?>\n<Root><Descricao>Atenção Básica\x00</Descricao></Root>'
    arquivo = tmp_path / "amostra.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    conteudo = read_xml_text(arquivo)

    assert "Atenção Básica" in conteudo
    assert "\x00" not in conteudo


def test_read_xml_text_respeita_encoding_declarado_utf_8(tmp_path) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Root><Descricao>Iluminação pública – Praça São José\x1f</Descricao></Root>"
    )
    arquivo = tmp_path / "utf8.xml"
    arquivo.write_text(xml, encoding="utf-8")

    conteudo = read_xml_text(arquivo)

    assert "Iluminação pública – Praça São José" in conteudo
    assert "\x1f" not in conteudo


def test_read_xml_text_respeita_bom_utf_8_sem_declaracao(tmp_path) -> None:
    arquivo = tmp_path / "bom.xml"
    arquivo.write_bytes("<Root><Descricao>Servidor João</Descricao></Root>".encode("utf-8-sig"))

    conteudo = read_xml_text(arquivo)

    assert "Servidor João" in conteudo
    assert "\ufeff" not in conteudo


def test_read_xml_text_usa_fallback_iso_8859_1_sem_declaracao(tmp_path) -> None:
    xml = "<Root><Descricao>Saúde Básica</Descricao></Root>"
    arquivo = tmp_path / "fallback.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    conteudo = read_xml_text(arquivo)

    assert "Saúde Básica" in conteudo


def test_parse_xml_root_preserva_acentos_e_ignora_controles_invalidos(tmp_path) -> None:
    xml = '<?xml version="1.0" encoding="ISO-8859-1"?>\n<Root><Nome>Educação\x1f Infantil</Nome></Root>'
    arquivo = tmp_path / "raiz.xml"
    arquivo.write_text(xml, encoding="ISO-8859-1")

    root = parse_xml_root(arquivo)

    assert root.findtext("./Nome") == "Educação Infantil"


def test_read_xml_text_falha_quando_encoding_declarado_nao_eh_suportado(
    tmp_path,
) -> None:
    arquivo = tmp_path / "encoding-invalido.xml"
    arquivo.write_bytes(b'<?xml version="1.0" encoding="X-INVALIDO"?>\n<Root><Nome>Teste</Nome></Root>')

    with pytest.raises(ValueError, match="encoding nao suportado: 'X-INVALIDO'"):
        read_xml_text(arquivo)


def test_read_xml_text_falha_quando_bytes_nao_batem_com_encoding_declarado(
    tmp_path,
) -> None:
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<Root><Nome>Atenção Básica</Nome></Root>'
    arquivo = tmp_path / "mismatch.xml"
    arquivo.write_bytes(xml.encode("ISO-8859-1"))

    with pytest.raises(
        ValueError,
        match="encoding declarado 'UTF-8'",
    ):
        read_xml_text(arquivo)


def test_sanitize_xml_payload_sanitiza_strings_aninhadas_sem_perder_whitespace() -> None:
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
