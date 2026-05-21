"""Parser XML para servidores (folha de pagamento)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class ServidoresParser:
    """Converte XML de servidores em lista de dicionários."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []

        for node in root.findall(".//FolhaPagamento"):
            nome = self._txt(node, "NomServidor")
            cargo = self._txt(node, "Cargo") or "nao_informado"
            secretaria = self._txt(node, "Lotacao") or "nao_informado"
            salario_base = self._money(node, "SalarioBase")
            data_admissao = self._competencia_as_date(node)

            if not nome or salario_base is None or not data_admissao:
                continue

            registros.append(
                {
                    "nome": nome,
                    "cargo": cargo,
                    "secretaria": secretaria,
                    "salario_base": salario_base,
                    "data_admissao": data_admissao,
                }
            )

        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    def _money(self, node: ET.Element, tag: str) -> Decimal | None:
        value = self._txt(node, tag)
        if not value:
            return None
        normalized = value.replace("R$", "").replace(".", "").replace(",", ".").strip()
        try:
            return Decimal(normalized)
        except Exception:
            return None

    def _competencia_as_date(self, node: ET.Element) -> str | None:
        competencia = self._txt(node, "Competencia")
        if not competencia or "/" not in competencia:
            return None
        mm, yyyy = competencia.split("/")
        return f"{yyyy}-{mm}-01"
