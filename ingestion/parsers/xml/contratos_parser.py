"""Parser XML para contratos."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class ContratosParser:
    """Converte XML de contratos em lista de dicionários."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []

        for node in root.findall(".//InstrumentoContratual"):
            numero = self._txt(node, "NumeroInstrumentoContratual") or self._txt(
                node, "NumeroLicitatorio"
            )
            fornecedor = self._txt(node, "NomeFornecedor")
            cnpj = self._txt(node, "CNPJFornecedor")
            valor = self._money(node, "ValorInstrumentoContratual")
            data_inicio = self._date(node, "DataEmissao")
            data_fim = self._date(node, "DataExpiracao")
            categoria = self._txt(node, "TipoContrato") or "nao_informado"
            secretaria = self._txt(node, "UnidadeGestora") or "nao_informado"
            descricao = self._txt(node, "Objeto")

            if (
                not numero
                or not fornecedor
                or not cnpj
                or valor is None
                or not data_inicio
            ):
                continue

            registros.append(
                {
                    "numero": numero,
                    "fornecedor": fornecedor,
                    "cnpj": cnpj,
                    "valor": valor,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                    "categoria": categoria,
                    "secretaria": secretaria,
                    "descricao": descricao,
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

    def _date(self, node: ET.Element, tag: str) -> str | None:
        value = self._txt(node, tag)
        if not value:
            return None
        if "/" in value:
            dd, mm, yyyy = value.split("/")
            return f"{yyyy}-{mm}-{dd}"
        return value
