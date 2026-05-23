"""Parser XML para receitas (arrecadacao e lancamentos)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class ReceitasParser:
    """Converte XMLs de receita em dicionários normalizados."""

    def parse_arrecadacoes(self, filepath: str) -> list[dict[str, Any]]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []
        for node in root.findall("./Arrecadacao"):
            exercicio = self._int(node, "Exercicio")
            mes = self._txt(node, "Mes")
            data_arrecadacao = self._date(node, "DataArrecadacao")
            unidade = self._txt(node, "UnidadeGestora")
            if exercicio is None or not mes or not data_arrecadacao or not unidade:
                continue
            natureza_node = node.find("NaturezaCategoria")
            natureza = {
                "identificacao": self._txt(natureza_node, "Identificacao")
                if natureza_node is not None
                else None,
                "nome": self._txt(natureza_node, "Nome")
                if natureza_node is not None
                else None,
                "nivel": self._int(natureza_node, "Nivel")
                if natureza_node is not None
                else None,
                "identificacao_superior": self._txt(
                    natureza_node, "IdentificacaoSuperior"
                )
                if natureza_node is not None
                else None,
            }
            registros.append(
                {
                    "exercicio": exercicio,
                    "mes": mes,
                    "data_arrecadacao": data_arrecadacao,
                    "unidade_gestora": unidade,
                    "natureza": natureza,
                    "fonte_recurso": self._txt(node, "FonteRecurso"),
                    "valor_previsto_bruto": self._money(node, "ValorPrevistoBruto"),
                    "valor_arrecadado_bruto": self._money(node, "ValorArrecadadoBruto"),
                    "valor_previsto_deducoes": self._money(
                        node, "ValorPrevistoDeducoes"
                    ),
                    "valor_realizado_deducoes": self._money(
                        node, "ValorRealizadoDeducoes"
                    ),
                    "valor_previsto_liquido": self._money(node, "ValorPrevistoLiquido"),
                    "valor_arrecadado_liquido": self._money(
                        node, "ValorArrecadadoLiquido"
                    ),
                }
            )
        return registros

    def parse_lancamentos(self, filepath: str) -> list[dict[str, Any]]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []
        for node in root.findall("./Lancamento"):
            exercicio = self._int(node, "Exercicio")
            mes = self._txt(node, "Mes")
            data_lanc = self._date(node, "DataLancamento")
            tipo_receita = self._txt(node, "TipoReceita")
            tributo = self._txt(node, "Tributo")
            if (
                exercicio is None
                or not mes
                or not data_lanc
                or not tipo_receita
                or not tributo
            ):
                continue
            registros.append(
                {
                    "exercicio": exercicio,
                    "mes": mes,
                    "data_lancamento": data_lanc,
                    "tipo_receita": tipo_receita,
                    "tributo": tributo,
                    "valor_lancado_exercicio": self._money(
                        node, "ValorLancadoExercicio"
                    ),
                    "valor_lancado_divida_ativa": self._money(
                        node, "ValorLancadoDividaAtiva"
                    ),
                    "valor_lancado_cobraca_judicial": self._money(
                        node, "ValorLancadoCobracaJudicial"
                    ),
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
        v = child.text.strip()
        return v or None

    def _money(self, node: ET.Element, tag: str) -> Decimal | None:
        v = self._txt(node, tag)
        if not v:
            return None
        n = v.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            return Decimal(n)
        except Exception:
            return None

    def _int(self, node: ET.Element | None, tag: str) -> int | None:
        v = self._txt(node, tag)
        if not v:
            return None
        try:
            return int(v)
        except Exception:
            return None

    def _date(self, node: ET.Element, tag: str) -> str | None:
        v = self._txt(node, tag)
        if not v:
            return None
        if "/" in v:
            dd, mm, yyyy = v.split("/")
            return f"{yyyy}-{mm}-{dd}"
        return v
