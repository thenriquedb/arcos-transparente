"""Parser XML para servidores (folha de pagamento)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.servidores import ServidorInSchema


class ServidoresParser:
    """Converte XML de servidores em lista de dicionários validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados com Pydantic."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for node in root.findall(".//FolhaPagamento"):
            payload_raw = {
                "nome": self._txt(node, "NomServidor"),
                "cargo": self._txt(node, "Cargo"),
                "secretaria": self._txt(node, "Lotacao"),
                "salario_base": self._txt(node, "SalarioBase"),
                "data_admissao": self._txt(node, "Competencia"),
            }

            try:
                payload = ServidorInSchema.model_validate(payload_raw)
            except ValidationError:
                invalidos += 1
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(
                f"Descartados {invalidos} registros invalidos de servidores em {filepath}"
            )

        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None
