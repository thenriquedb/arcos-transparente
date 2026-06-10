"""Parser XML para planejamentos orcamentarios."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root
from ingestion.schemas.planejamentos import PlanejamentoDespesaInSchema


class PlanejamentosParser:
    """Converte XML de planejamento em registros normalizados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        root = parse_xml_root(filepath)
        origem = self._infer_origem(filepath)
        registros: list[dict[str, Any]] = []

        for node in root.findall("./Principal"):
            payload_raw = {
                "origem": origem,
                "exercicio": self._txt(node, "Exercicio"),
                "unidade_gestora": self._txt(node, "UnidadeGestora"),
                "orgao": self._txt(node, "Orgao"),
                "unidade": self._txt(node, "Unidade"),
                "departamento": self._txt(node, "Departamento"),
                "funcao": self._txt(node, "Funcao"),
                "subfuncao": self._txt(node, "SubFuncao"),
                "programa": self._txt(node, "Programa"),
                "tipo_acao": self._txt(node, "TipoAcao"),
                "descricao_acao": self._txt(node, "DescricaoAcao"),
                "fonte_recurso_identificacao": self._nested_txt(node, "FonteRecurso", "Identificacao"),
                "fonte_recurso_descricao": self._nested_txt(node, "FonteRecurso", "Descricao"),
                "esfera_administrativa": self._txt(node, "EsferaAdministrativa"),
                "categoria_economica_identificacao": self._nested_txt(node, "CategoriaEconomica", "Identificacao"),
                "categoria_economica_descricao": self._nested_txt(node, "CategoriaEconomica", "Descricao"),
                "grupo_despesa_identificacao": self._nested_txt(node, "GrupoDespesa", "Identificacao"),
                "grupo_despesa_descricao": self._nested_txt(node, "GrupoDespesa", "Descricao"),
                "elemento_despesa_identificacao": self._nested_txt(node, "ElementoDespesa", "Identificacao"),
                "elemento_despesa_descricao": self._nested_txt(node, "ElementoDespesa", "Descricao"),
                "modalidade_aplicacao_identificacao": self._nested_txt(node, "ModalidadeAplicacao", "Identificacao"),
                "modalidade_aplicacao_descricao": self._nested_txt(node, "ModalidadeAplicacao", "Descricao"),
                "mes": self._txt(node, "Mes"),
                "dotacao_inicial": self._txt(node, "DotacaoInicial"),
                "creditos_adicionais": self._txt(node, "CreditosAdicionais"),
                "dotacao_atualizada": self._txt(node, "DotacaoAtualizada"),
                "valor_empenhado": self._txt(node, "ValorEmpenhado"),
                "valor_liquidacao": self._txt(node, "ValorLiquidacao"),
                "valor_liquidado": self._txt(node, "ValorLiquidado"),
                "valor_pago": self._txt(node, "ValorPago"),
                "valor_anulado": self._txt(node, "ValorAnulado"),
            }

            try:
                payload = PlanejamentoDespesaInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                logger.warning(f"Descartando planejamento invalido: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        return registros

    @staticmethod
    def _infer_origem(filepath: str) -> str:
        nome = Path(filepath).name.lower()
        if "saude" in nome or "saúde" in nome:
            return "saude"
        if "prefeitura" in nome:
            return "prefeitura"
        return "nao_informado"

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None

    def _nested_txt(self, node: ET.Element, parent_tag: str, child_tag: str) -> str | None:
        parent = node.find(parent_tag)
        if parent is None:
            return None
        return self._txt(parent, child_tag)
