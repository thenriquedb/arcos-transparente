"""Parser XML para licitações."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class LicitacoesParser:
    """Converte XML de licitações em lista de dicionários."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê arquivo XML e retorna registros normalizados."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []

        for node in root.findall(".//ProcessoLicitatorio"):
            numero = self._txt(node, "NumeroProcesso")
            modalidade = self._txt(node, "Modalidade")
            objeto = self._txt(node, "Objeto")
            valor_estimado = self._money(node, "ValorProcesso")
            data_abertura = self._date(node, "DataJulgamento") or self._date(
                node, "DataHomologacao"
            )
            situacao = self._txt(node, "SituacaoProcesso") or "nao_informado"
            secretaria = self._txt(node, "UnidadeGestora") or "nao_informado"

            if (
                not numero
                or not modalidade
                or not objeto
                or valor_estimado is None
                or not data_abertura
            ):
                continue

            registros.append(
                {
                    "numero": numero,
                    "modalidade": modalidade,
                    "objeto": objeto,
                    "valor_estimado": valor_estimado,
                    "data_abertura": data_abertura,
                    "situacao": situacao,
                    "secretaria": secretaria,
                    "vencedores": self._parse_vencedores(node),
                    "instrumentos_contratuais": self._parse_instrumentos(node),
                }
            )

        return registros

    def _parse_vencedores(self, node: ET.Element) -> list[dict[str, Any]]:
        vencedores: list[dict[str, Any]] = []
        for item in node.findall("./Vencedores/Vencedor"):
            cnpj_cpf = self._txt(item, "CNPJCPF")
            nome = self._txt(item, "NomeFantasia")
            validade = self._txt(item, "ValidadeDaProposta")
            if not cnpj_cpf or not nome:
                continue
            vencedores.append(
                {
                    "cnpj_cpf": cnpj_cpf,
                    "nome": nome,
                    "validade_proposta": validade,
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
                    "data_emissao": self._date(item, "DataEmissao"),
                    "data_expiracao": self._date(item, "DataExpiracao"),
                    "cnpj_fornecedor": self._txt(item, "CNPJFornecedor"),
                    "nome_fornecedor": self._txt(item, "NomeFornecedor"),
                    "possui_aditivo": self._txt(item, "PossuiAditivo"),
                    "valor_instrumento_contratual": self._money(
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
                    "quantidade": self._decimal(item, "Quantidade"),
                    "valor_unitario": self._money(item, "ValorUnitario"),
                    "valor_total": self._money(item, "ValorTotal"),
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

    def _decimal(self, node: ET.Element, tag: str) -> Decimal | None:
        value = self._txt(node, tag)
        if not value:
            return None
        normalized = value.replace(".", "").replace(",", ".").strip()
        try:
            return Decimal(normalized)
        except Exception:
            return None
