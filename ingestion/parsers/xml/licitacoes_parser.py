"""Parser XML para licitações."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.licitacoes import LicitacaoInSchema


class LicitacoesParser:
    """Converte XML de licitações em lista de dicionários validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados com Pydantic."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []

        for node in root.findall(".//ProcessoLicitatorio"):
            payload_raw = {
                "numero": self._txt(node, "NumeroProcesso"),
                "modalidade": self._txt(node, "Modalidade"),
                "objeto": self._txt(node, "Objeto"),
                "valor_estimado": self._txt(node, "ValorProcesso"),
                "data_abertura": self._txt(node, "DataJulgamento")
                or self._txt(node, "DataHomologacao"),
                "situacao": self._txt(node, "SituacaoProcesso"),
                "secretaria": self._txt(node, "UnidadeGestora"),
                "vencedores": self._parse_vencedores(node),
                "instrumentos_contratuais": self._parse_instrumentos(node),
            }

            try:
                payload = LicitacaoInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                logger.warning(f"Descartando licitacao invalida: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        return registros

    def _parse_vencedores(self, node: ET.Element) -> list[dict[str, Any]]:
        vencedores: list[dict[str, Any]] = []
        for item in node.findall("./Vencedores/Vencedor"):
            vencedores.append(
                {
                    "cnpj_cpf": self._txt(item, "CNPJCPF"),
                    "nome": self._txt(item, "NomeFantasia"),
                    "validade_proposta": self._txt(item, "ValidadeDaProposta"),
                }
            )
        return vencedores

    def _parse_instrumentos(self, node: ET.Element) -> list[dict[str, Any]]:
        instrumentos: list[dict[str, Any]] = []
        for item in node.findall("./InstrumentosContratuais/InstrumentoContratual"):
            instrumentos.append(
                {
                    "numero_licitatorio": self._txt(item, "NumeroLicitatorio"),
                    "unidade_gestora": self._txt(item, "UnidadeGestora"),
                    "tipo_instrumento_contratual": self._txt(
                        item, "TipoInstrumentoContratual"
                    ),
                    "numero_instrumento": self._txt(
                        item, "NumeroInstrumentoContratual"
                    ),
                    "tipo_contrato": self._txt(item, "TipoContrato"),
                    "objeto": self._txt(item, "Objeto"),
                    "data_emissao": self._txt(item, "DataEmissao"),
                    "data_expiracao": self._txt(item, "DataExpiracao"),
                    "cnpj_fornecedor": self._txt(item, "CNPJFornecedor"),
                    "nome_fornecedor": self._txt(item, "NomeFornecedor"),
                    "possui_aditivo": self._txt(item, "PossuiAditivo"),
                    "valor_instrumento_contratual": self._txt(
                        item, "ValorInstrumentoContratual"
                    ),
                    "materias": self._parse_materias(item),
                }
            )
        return instrumentos

    def _parse_materias(self, instrumento_node: ET.Element) -> list[dict[str, Any]]:
        materias: list[dict[str, Any]] = []
        for item in instrumento_node.findall("./ItensAdquiridos/Item"):
            materias.append(
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
        return materias

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None
