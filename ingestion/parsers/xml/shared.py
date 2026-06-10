"""Helpers compartilhados para leitura e sanitizacao de XML."""

from __future__ import annotations

import codecs
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

XML_FALLBACK_ENCODING = "ISO-8859-1"
_ALLOWED_CONTROL_CODES = {9, 10, 13}
_XML_DECLARATION_ENCODING_PATTERN = re.compile(
    rb"""<\?xml[^>]*encoding\s*=\s*['"]([A-Za-z][A-Za-z0-9._-]*)['"]""",
    re.IGNORECASE,
)
_BYTE_ORDER_MARK_ENCODINGS = (
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_BE, "utf-16"),
    (codecs.BOM_UTF16_LE, "utf-16"),
)


@dataclass(frozen=True)
class XmlEncodingResolution:
    """Resultado da resolução de encoding do XML antes da decodificação."""

    encoding: str
    source: str
    declared_encoding: str | None = None


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
    """Lê bytes do XML respeitando BOM/declaration e sanitiza o texto."""

    xml_bytes = Path(filepath).read_bytes()
    resolution = _resolve_xml_encoding(xml_bytes)

    try:
        text = xml_bytes.decode(resolution.encoding)
    except UnicodeDecodeError as exc:
        if resolution.source == "declaration":
            raise ValueError(
                f"Falha ao decodificar XML '{filepath}' com o encoding declarado '{resolution.declared_encoding}'."
            ) from exc
        if resolution.source == "bom":
            raise ValueError(
                f"Falha ao decodificar XML '{filepath}' com o encoding detectado pelo BOM '{resolution.encoding}'."
            ) from exc
        raise ValueError(
            f"Falha ao decodificar XML '{filepath}' com o encoding de fallback '{resolution.encoding}'."
        ) from exc

    return sanitize_xml_text(text) or ""


def parse_xml_root(filepath: str | Path) -> ET.Element:
    """Retorna a raiz XML a partir do texto sanitizado e já decodificado."""

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


def _resolve_xml_encoding(xml_bytes: bytes) -> XmlEncodingResolution:
    bom_resolution = _resolve_bom_encoding(xml_bytes)
    if bom_resolution is not None:
        return bom_resolution

    declared_encoding = _extract_declared_xml_encoding(xml_bytes)
    if declared_encoding is None:
        return XmlEncodingResolution(
            encoding=XML_FALLBACK_ENCODING,
            source="fallback",
        )

    try:
        normalized_encoding = codecs.lookup(declared_encoding).name
    except LookupError as exc:
        raise ValueError(f"XML declara encoding nao suportado: '{declared_encoding}'.") from exc

    return XmlEncodingResolution(
        encoding=normalized_encoding,
        source="declaration",
        declared_encoding=declared_encoding,
    )


def _resolve_bom_encoding(xml_bytes: bytes) -> XmlEncodingResolution | None:
    for bom, encoding in _BYTE_ORDER_MARK_ENCODINGS:
        if xml_bytes.startswith(bom):
            return XmlEncodingResolution(
                encoding=encoding,
                source="bom",
            )
    return None


def _extract_declared_xml_encoding(xml_bytes: bytes) -> str | None:
    head = xml_bytes[:256]
    match = _XML_DECLARATION_ENCODING_PATTERN.search(head)
    if match is None:
        return None
    return match.group(1).decode("ascii")
