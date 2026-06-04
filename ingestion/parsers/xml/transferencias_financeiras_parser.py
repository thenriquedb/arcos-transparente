"""Parser XML para movimentos de transferencias financeiras."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from typing import Any

from ingestion.parsers.xml.shared import parse_xml_root


class TransferenciasFinanceirasParser:
    """Converte XMLs de transferencias financeiras em registros SQL-ready."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        root = parse_xml_root(filepath)
        registros: list[dict[str, Any]] = []
        arquivo_origem = Path(filepath).name

        for sequencia, node in enumerate(
            root.findall("./TransferenciaFinanceira"),
            start=1,
        ):
            data_movimento = self._date(node, "DataMovimento")
            unidade_concessora = self._txt(node, "UnidadeGestoraConcessora")
            unidade_recebedora = self._txt(node, "UnidadeGestoraRecebedora")
            if not data_movimento or not unidade_concessora or not unidade_recebedora:
                continue

            registros.append(
                {
                    "arquivo_origem": arquivo_origem,
                    "sequencia_origem": sequencia,
                    "exercicio": int(data_movimento[:4]),
                    "identificacao": self._txt(node, "Identificacao"),
                    "unidade_gestora_concessora": unidade_concessora,
                    "unidade_gestora_recebedora": unidade_recebedora,
                    "finalidade": self._txt(node, "Finalidade"),
                    "fonte_recurso": self._txt(node, "FonteRecurso"),
                    "detalhamento_fonte": self._txt(node, "DetalhamentoFonte"),
                    "programacao_inicial": self._money(node, "ProgramacaoInicial"),
                    "data_movimento": data_movimento,
                    "tipo_movimento": self._txt(node, "TipoMovimento"),
                    "valor_movimento": self._money(node, "ValorMovimento"),
                }
            )

        return registros

    @staticmethod
    def _txt(node: ET.Element | None, tag: str) -> str | None:
        if node is None:
            return None
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    def _money(self, node: ET.Element, tag: str) -> Decimal | None:
        value = self._txt(node, tag)
        if not value:
            return None
        normalized = value.replace("R$", "").replace(" ", "").replace(".", "")
        normalized = normalized.replace(",", ".")
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
