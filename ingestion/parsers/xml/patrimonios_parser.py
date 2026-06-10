"""Parser XML para bens patrimoniais."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root
from ingestion.schemas.patrimonios import PatrimonioInSchema


class PatrimoniosParser:
    """Converte XML de patrimonio em registros validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        root = parse_xml_root(filepath)
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for ordem, node in enumerate(root.findall("./ITEM"), start=1):
            placa = self._txt(node, "PLACA") or f"sem_placa_{ordem:05d}"
            payload_raw = {
                "unidade_gestora": self._txt(node, "UnidadeGestora"),
                "placa": placa,
                "situacao_bem": self._txt(node, "SITUACAOBEM"),
                "comandatario": self._txt(node, "COMANDATARIO"),
                "classificacao": self._txt(node, "CLASSIFICACAO"),
                "descricao_item": self._txt(node, "DESCRICAOITEM"),
                "tipo_ingresso": self._txt(node, "TIPOINGRESSO"),
                "data_aquisicao": self._txt(node, "DATAAQUISICAO"),
                "data_baixa": self._txt(node, "DATABAIXA"),
                "localizacao": self._txt(node, "LOCALIZACAO"),
                "status": self._txt(node, "STATUS"),
                "valor_ingresso": self._txt(node, "VALORINGRESSO"),
                "valor_atualizado": self._txt(node, "VALORATUALIZADO"),
            }

            try:
                payload = PatrimonioInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando patrimonio invalido: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartados {invalidos} registros invalidos de patrimonio em {filepath}")

        return registros

    @staticmethod
    def _txt(node: ET.Element, tag: str) -> str | None:
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None
