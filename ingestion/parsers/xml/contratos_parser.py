"""Parser XML para contratos."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root, serialize_xml_node
from ingestion.schemas.contratos import ContratoInSchema


class ContratosParser:
    """Converte XML de contratos em lista de dicionários validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados com Pydantic."""
        root = parse_xml_root(filepath)
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for node in root.findall(".//InstrumentoContratual"):
            payload_raw = {
                "numero": self._txt(node, "NumeroInstrumentoContratual") or self._txt(node, "NumeroLicitatorio"),
                "numero_licitatorio": self._txt(node, "NumeroLicitatorio"),
                "numero_instrumento": self._txt(node, "NumeroInstrumentoContratual"),
                "tipo_instrumento_contratual": self._txt(node, "TipoInstrumentoContratual"),
                "fornecedor": self._txt(node, "NomeFornecedor"),
                "cnpj": self._txt(node, "CNPJFornecedor"),
                "valor": self._txt(node, "ValorInstrumentoContratual"),
                "data_inicio": self._txt(node, "DataEmissao"),
                "data_fim": self._txt(node, "DataExpiracao"),
                "categoria": self._txt(node, "TipoContrato"),
                "secretaria": self._txt(node, "UnidadeGestora"),
                "possui_aditivo": self._txt(node, "PossuiAditivo"),
                "descricao": self._txt(node, "Objeto"),
                "descricao_despesa": self._join_unique_texts(
                    node.findall(".//DespesasOrcamentarias/DespesaOrcamentaria/DescricaoDespesa")
                ),
                "xml_original": serialize_xml_node(node),
                "despesas_orcamentarias": self._parse_despesas_orcamentarias(node),
                "itens_adquiridos": self._parse_itens_adquiridos(node),
            }

            try:
                payload = ContratoInSchema.model_validate(payload_raw)
            except ValidationError:
                invalidos += 1
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartados {invalidos} registros invalidos de contratos em {filepath}")

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

    def _parse_despesas_orcamentarias(self, node: ET.Element) -> list[dict[str, Any]]:
        despesas: list[dict[str, Any]] = []
        for item in node.findall("./DespesasOrcamentarias/DespesaOrcamentaria"):
            despesas.append(
                {
                    "unidade_gestora": self._txt(item, "UnidadeGestora"),
                    "exercicio": self._txt(item, "Exercicio"),
                    "orgao": self._txt(item, "Orgao"),
                    "unidade": self._txt(item, "Unidade"),
                    "departamento": self._txt(item, "Departamento"),
                    "fonte_recurso": self._txt(item, "FonteRecurso"),
                    "natureza_despesa_rubrica": self._txt(item, "NaturezaDespesaRubrica"),
                    "descricao_despesa": self._txt(item, "DescricaoDespesa"),
                    "valor_despesa": self._txt(item, "ValorDespesa"),
                }
            )
        return despesas

    def _parse_itens_adquiridos(self, node: ET.Element) -> list[dict[str, Any]]:
        itens: list[dict[str, Any]] = []
        for item in node.findall("./ItensAdquiridos/Item"):
            itens.append(
                {
                    "unidade_gestora": self._txt(item, "UnidadeGestora"),
                    "numero_lote": self._txt(item, "NumeroLote"),
                    "numero_item": self._txt(item, "NumeroItem"),
                    "identificacao": self._txt(item, "Identificacao"),
                    "quantidade": self._txt(item, "Quantidade"),
                    "valor_unitario": self._txt(item, "ValorUnitario"),
                    "valor_total": self._txt(item, "ValorTotal"),
                }
            )
        return itens
