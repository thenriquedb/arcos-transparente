"""Parser XML para folha de pagamento."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any


class FolhaPagamentoParser:
    """Converte XML de folha em registros normalizados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        registros: list[dict[str, Any]] = []
        for node in root.findall("./FolhaPagamento"):
            competencia = self._competencia(node, "Competencia")
            nome = self._txt(node, "NomServidor")
            if not competencia or not nome:
                continue
            registros.append(
                {
                    "competencia_ano": competencia["ano"],
                    "competencia_mes_nome": competencia["mes_nome"],
                    "competencia_mes_num": competencia["mes_num"],
                    "nome_servidor": nome,
                    "lotacao": self._txt(node, "Lotacao"),
                    "cargo": self._txt(node, "Cargo"),
                    "salario_base": self._money(node, "SalarioBase"),
                    "proventos": self._money(node, "Proventos"),
                    "vantagens": self._money(node, "Vantagens"),
                    "vencimentos_totais": self._money(node, "VencimentosTotais"),
                    "descontos": self._money(node, "Descontos"),
                    "liquido": self._money(node, "Liquido"),
                }
            )
        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        c = node.find(tag)
        if c is None or c.text is None:
            return None
        v = c.text.strip()
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

    def _competencia(self, node: ET.Element, tag: str) -> dict[str, Any] | None:
        v = self._txt(node, tag)
        if not v or "/" not in v:
            return None
        mm, yyyy = v.split("/")
        mes_num = int(mm)
        mapa = {
            1: "JANEIRO",
            2: "FEVEREIRO",
            3: "MARCO",
            4: "ABRIL",
            5: "MAIO",
            6: "JUNHO",
            7: "JULHO",
            8: "AGOSTO",
            9: "SETEMBRO",
            10: "OUTUBRO",
            11: "NOVEMBRO",
            12: "DEZEMBRO",
        }
        return {"ano": int(yyyy), "mes_num": mes_num, "mes_nome": mapa.get(mes_num, "DESCONHECIDO")}
