"""Parser XML para contratos."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.contratos import ContratoInSchema


class ContratosParser:
    """Converte XML de contratos em lista de dicionários validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados com Pydantic."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for node in root.findall(".//InstrumentoContratual"):
            payload_raw = {
                "numero": self._txt(node, "NumeroInstrumentoContratual")
                or self._txt(node, "NumeroLicitatorio"),
                "fornecedor": self._txt(node, "NomeFornecedor"),
                "cnpj": self._txt(node, "CNPJFornecedor"),
                "valor": self._txt(node, "ValorInstrumentoContratual"),
                "data_inicio": self._txt(node, "DataEmissao"),
                "data_fim": self._txt(node, "DataExpiracao"),
                "categoria": self._txt(node, "TipoContrato"),
                "secretaria": self._txt(node, "UnidadeGestora"),
                "descricao": self._txt(node, "Objeto"),
                "descricao_despesa": self._join_unique_texts(
                    node.findall(
                        ".//DespesasOrcamentarias/DespesaOrcamentaria/DescricaoDespesa"
                    )
                ),
            }

            try:
                payload = ContratoInSchema.model_validate(payload_raw)
            except ValidationError:
                invalidos += 1
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(
                f"Descartados {invalidos} registros invalidos de contratos em {filepath}"
            )

        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    @staticmethod
    def _join_unique_texts(nodes: list[ET.Element]) -> str | None:
        values: list[str] = []
        seen: set[str] = set()

        for node in nodes:
            if node.text is None:
                continue
            value = node.text.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            values.append(value)

        if not values:
            return None
        return " | ".join(values)
