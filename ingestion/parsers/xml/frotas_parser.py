"""Parser XML para frota administrativa."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class FrotasParser:
    """Converte XML de frotas em lista de dicionários normalizados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Lê XML e retorna veículos com despesas aninhadas."""
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []

        for node in root.findall("./Frotas"):
            codigo_veiculo = self._txt(node, "CodigoVeiculo")
            if not codigo_veiculo:
                continue

            registros.append(
                {
                    "codigo_veiculo": codigo_veiculo,
                    "placa_patrimonio": self._txt(node, "PlacaPatrimonio"),
                    "placa_veiculo": self._txt(node, "PlacaVeiculo"),
                    "descricao_material": self._txt(node, "DescricaoMaterial"),
                    "unidade_gestora": self._txt(node, "DescricaoUnidadeGestora"),
                    "tipo_veiculo": self._txt(node, "TipoVeiculo"),
                    "marca": self._txt(node, "Marca"),
                    "modelo": self._txt(node, "Modelo"),
                    "data_aquisicao": self._txt(node, "dataAquisicao"),
                    "localizacao": self._txt(node, "Localizacao"),
                    "descricao": self._txt(node, "Descricao"),
                    "ano_fabricacao": self._int(node, "AnoFabricacao"),
                    "situacao_veiculo": self._txt(node, "SituacaoVeiculo"),
                    "situacao_veiculo_patrimonio": self._txt(node, "SituacaoVeiculoPatrimonio"),
                    "estado_conservacao": self._txt(node, "EstadoConservacao"),
                    "renavam": self._txt(node, "Renavam"),
                    "chassi": self._txt(node, "Chassi"),
                    "ano_modelo": self._int(node, "AnoModelo"),
                    "qtd_passageiros": self._int(node, "QtdPassageiros"),
                    "marcador_atual": self._decimal(node, "MarcadorAtual"),
                    "unidade_medida": self._txt(node, "UnidadeMedida"),
                    "fornecedor": self._txt(node, "Fornecedor"),
                    "cor_predominante": self._txt(node, "CorPredominante"),
                    "valor_atual": self._decimal(node, "ValorAtual"),
                    "despesas": self._parse_despesas(node),
                }
            )

        return registros

    def _parse_despesas(self, veiculo_node: ET.Element) -> list[dict[str, Any]]:
        despesas: list[dict[str, Any]] = []
        for node in veiculo_node.findall("./FrotasDespesas/FrotasDespesas"):
            despesas.append(
                {
                    "descricao_evento": self._txt(node, "DescricaoEvento"),
                    "quantidade_lancamento": self._decimal(node, "QuantidadeLancamento"),
                    "valor_lancamento": self._decimal(node, "ValorLancamento"),
                    "data_evento": self._date(node, "DataEvento"),
                    "tp_despesa": self._txt(node, "tp_Despesa"),
                    "tipo_despesa": self._txt(node, "TipoDespesa"),
                    "total_despesa": self._decimal(node, "TotalDespesa"),
                }
            )
        return despesas

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    def _int(self, node: ET.Element, tag: str) -> int | None:
        value = self._txt(node, tag)
        if not value:
            return None
        try:
            return int(value)
        except Exception:
            return None

    def _decimal(self, node: ET.Element, tag: str) -> Decimal | None:
        value = self._txt(node, tag)
        if not value:
            return None
        normalized = value.replace(".", "").replace(",", ".") if "," in value else value
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
