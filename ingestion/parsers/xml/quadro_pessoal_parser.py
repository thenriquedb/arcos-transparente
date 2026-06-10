"""Parser XML para quadro de pessoal."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import read_xml_text
from ingestion.schemas.quadro_pessoal import QuadroPessoalInSchema


class QuadroPessoalParser:
    """Converte XML de quadro de pessoal em registros validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        # Um dos arquivos de origem vem com alguns fechamentos ausentes. Como os
        # registros sao planos, a leitura por blocos preserva os dados aproveitaveis.
        text = read_xml_text(filepath)
        origem = self._infer_origem(filepath)
        registros: list[dict[str, Any]] = []
        invalidos = 0

        for ordem, block in enumerate(self._iter_blocks(text), start=1):
            payload_raw = {
                "origem": origem,
                "competencia_referencia": self._tag_text(block, "Competencia"),
                "regime_contratacao": self._tag_text(block, "RegimeContratacao"),
                "vagas_criadas": self._tag_text(block, "VagasCriadas"),
                "vagas_preenchidas": self._tag_text(block, "VagasPreenchidas"),
            }
            try:
                payload = QuadroPessoalInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando quadro de pessoal invalido #{ordem}: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartados {invalidos} registros invalidos de quadro pessoal em {filepath}")

        return registros

    @staticmethod
    def _iter_blocks(text: str) -> list[str]:
        starts = [match.start() for match in re.finditer(r"<QuadroPessoal>", text)]
        blocks: list[str] = []
        for index, start in enumerate(starts):
            next_start = starts[index + 1] if index + 1 < len(starts) else len(text)
            end_tag = text.find("</QuadroPessoal>", start, next_start)
            end = end_tag + len("</QuadroPessoal>") if end_tag != -1 else next_start
            blocks.append(text[start:end])
        return blocks

    @staticmethod
    def _tag_text(block: str, tag: str) -> str | None:
        match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", block, re.DOTALL)
        if match is None:
            if re.search(rf"<{tag}\s*/>", block):
                return None
            return None
        value = match.group(1).strip()
        return value or None

    @staticmethod
    def _infer_origem(filepath: str) -> str:
        nome = Path(filepath).name.lower()
        if "saude" in nome or "saúde" in nome:
            return "saude"
        if "prefeitura" in nome:
            return "prefeitura"
        if "camara" in nome or "câmara" in nome:
            return "camara"
        return "nao_informado"
