"""Parser XML para politicos eleitos."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root
from ingestion.schemas.eleitos import EleitoInSchema


class EleitosParser:
    """Converte XML de eleitos em registros validados por mandato."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados com Pydantic."""
        root = parse_xml_root(filepath)
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for secao_tag, item_tag, tipo_politico in (
            (
                "vereadores",
                "vereador",
                "vereador",
            ),
            ("prefeitos", "prefeito", "prefeito"),
            ("vicePrefeitos", "vicePrefeito", "vice-prefeito"),
        ):
            secao = root.find(secao_tag)
            if secao is None:
                continue

            municipio = secao.attrib.get("municipio") or "nao_informado"
            estado = secao.attrib.get("estado") or "nao_informado"

            for pessoa in secao.findall(item_tag):
                mandatos = pessoa.findall("./mandatos/mandato")
                for mandato in mandatos:
                    payload_raw = {
                        "tipo_politico": tipo_politico,
                        "id_origem": pessoa.attrib.get("id"),
                        "municipio": municipio,
                        "estado": estado,
                        "nome_completo": self._txt(pessoa, "nomeCompleto"),
                        "nome_popular": self._txt(pessoa, "nomePopular"),
                        "partido": self._txt(pessoa, "partido"),
                        "telefone": self._txt(pessoa, "telefone"),
                        "email": self._txt(pessoa, "email"),
                        "homepage": self._txt(pessoa, "homepage"),
                        "numero_gabinete": self._txt(pessoa, "numerogabinete"),
                        "cargo": self._txt(pessoa, "cargo"),
                        "biografia": self._txt(pessoa, "biografia"),
                        "mandato_inicio": self._txt(mandato, "inicio"),
                        "mandato_fim": self._txt(mandato, "fim"),
                        "mandato_status": self._txt(mandato, "status"),
                        "mandato_observacao": self._txt(mandato, "observacao"),
                    }
                    try:
                        payload = EleitoInSchema.model_validate(payload_raw)
                    except ValidationError:
                        invalidos += 1
                        continue

                    registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(
                f"Descartados {invalidos} registros invalidos de eleitos em {filepath}"
            )

        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None
