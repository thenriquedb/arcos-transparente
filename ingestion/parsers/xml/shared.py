"""Helpers compartilhados para leitura e sanitizacao de XML."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

XML_SOURCE_ENCODING = "ISO-8859-1"
_ALLOWED_CONTROL_CODES = {9, 10, 13}


def sanitize_xml_text(value: str | None) -> str | None:
    """Remove caracteres de controle invalidos preservando whitespace comum."""

    if value is None:
        return None

    sanitized = "".join(char for char in value if _is_allowed_character(ord(char)))
    return sanitized


def sanitize_xml_payload(value: Any) -> Any:
    """Sanitiza recursivamente strings dentro de payloads aninhados."""

    if isinstance(value, str):
        return sanitize_xml_text(value)
    if isinstance(value, list):
        return [sanitize_xml_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_xml_payload(item) for item in value)
    if isinstance(value, dict):
        return {key: sanitize_xml_payload(item) for key, item in value.items()}
    return value


def read_xml_text(filepath: str | Path) -> str:
    """Lê bytes do XML usando ISO-8859-1 e sanitiza o texto resultante."""

    xml_bytes = Path(filepath).read_bytes()
    text = xml_bytes.decode(XML_SOURCE_ENCODING)
    return sanitize_xml_text(text) or ""


def parse_xml_root(filepath: str | Path) -> ET.Element:
    """Retorna a raiz XML a partir do texto sanitizado lido com ISO-8859-1."""

    return ET.fromstring(read_xml_text(filepath))


def serialize_xml_node(node: ET.Element) -> str:
    """Serializa um no XML em texto sanitizado."""

    return sanitize_xml_text(ET.tostring(node, encoding="unicode")) or ""


def _is_allowed_character(codepoint: int) -> bool:
    if codepoint in _ALLOWED_CONTROL_CODES:
        return True
    if 0 <= codepoint <= 31:
        return False
    if 127 <= codepoint <= 159:
        return False
    return True
