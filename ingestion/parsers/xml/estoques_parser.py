"""Parser XML para dados de estoque administrativo."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.parsers.xml.shared import parse_xml_root
from ingestion.schemas.estoques import (
    EstoqueMaterialInSchema,
    EstoqueMovimentacaoInSchema,
)
from shared.utils.text import normalize_search_text
from shared.utils.validation import parse_date


class EstoquesParser:
    """Converte XMLs de estoque em materiais com movimentacoes aninhadas."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        root = parse_xml_root(filepath)
        if normalize_search_text(root.tag) != "estoque":
            raise ValueError("XML de estoques deve possuir raiz ESTOQUE")

        material_nodes = root.findall("./MATERIAL")
        if not material_nodes:
            if len(root) == 0 and not (root.text or "").strip():
                logger.warning(f"Ignorando XML de estoques vazio em {filepath}")
                return []
            raise ValueError("XML de estoques nao contem materiais suportados")

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for sequencia_material, node in enumerate(material_nodes, start=1):
            summary = node.find("./MOVIMENTACAOSUMARIZADA")
            if summary is None:
                invalidos += 1
                logger.warning(f"Descartando material de estoque sem MOVIMENTACAOSUMARIZADA em {filepath}")
                continue

            try:
                periodo_inicio, periodo_fim = self._parse_period(self._txt(summary, "Periodo"))
            except ValueError as exc:
                invalidos += 1
                logger.warning(f"Descartando material de estoque com periodo invalido em {filepath}: {exc}")
                continue

            movimentacoes = self._parse_movimentacoes(
                node,
                filepath=filepath,
                sequencia_material=sequencia_material,
            )
            payload_raw = {
                "arquivo_origem": Path(filepath).name,
                "sequencia_material": sequencia_material,
                "origem": self._infer_origem(filepath, movimentacoes),
                "exercicio": periodo_fim.year,
                "material": self._txt(node, "Material"),
                "unidade_medida": self._txt(node, "UnidadeMedida"),
                "periodo_inicio": periodo_inicio,
                "periodo_fim": periodo_fim,
                "saldo_anterior_quantidade": self._txt(summary, "SaldoAnteriorQuantidade"),
                "saldo_anterior_valor": self._txt(summary, "SaldoAnteriorValor"),
                "entrada_quantidade": self._txt(summary, "EntradaQuantidade"),
                "entrada_valor": self._txt(summary, "EntradaValor"),
                "saida_quantidade": self._txt(summary, "SaidaQuantidade"),
                "saida_valor": self._txt(summary, "SaidaValor"),
                "saldo_quantidade": self._txt(summary, "SaldoQuantidade"),
                "saldo_valor": self._txt(summary, "SaldoValor"),
                "movimentacoes": movimentacoes,
            }

            try:
                payload = EstoqueMaterialInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                invalidos += 1
                logger.warning(f"Descartando material de estoque invalido: {exc}")
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartados {invalidos} registros invalidos de estoque em {filepath}")

        return registros

    def _parse_movimentacoes(
        self,
        material_node,
        *,
        filepath: str,
        sequencia_material: int,
    ) -> list[dict[str, Any]]:
        movimentacoes: list[dict[str, Any]] = []

        for sequencia_movimentacao, node in enumerate(
            material_node.findall("./MOVIMENTACAODIARIA/MOVIMENTACAODIARIA"),
            start=1,
        ):
            payload_raw = {
                "sequencia_movimentacao": sequencia_movimentacao,
                "data_movimento": self._txt(node, "DataMovimento"),
                "tipo_movimento": self._txt(node, "TipoMovimento"),
                "unidade_gestora": self._txt(node, "UnidadeGestora"),
                "almoxarifado": self._txt(node, "Almoxarifado"),
                "localizacao": self._txt(node, "Localizacao"),
                "classificacao": self._txt(node, "Classificacao"),
                "quantidade": self._txt(node, "Quantidade"),
                "valor_unitario": self._txt(node, "ValorUnitario"),
                "valor_total": self._txt(node, "ValorTotal"),
                "custo_medio": self._txt(node, "CustoMedio"),
            }

            try:
                payload = EstoqueMovimentacaoInSchema.model_validate(payload_raw)
            except ValidationError as exc:
                logger.warning(
                    f"Descartando movimentacao invalida do material {sequencia_material} em {filepath}: {exc}"
                )
                continue

            movimentacoes.append(payload.model_dump(mode="python"))

        return movimentacoes

    @staticmethod
    def _parse_period(periodo: str | None) -> tuple[date, date]:
        if not periodo:
            raise ValueError("Periodo obrigatorio ausente")
        if " a " in periodo:
            inicio_txt, fim_txt = [part.strip() for part in periodo.split(" a ", maxsplit=1)]
            inicio = parse_date(inicio_txt)
            fim = parse_date(fim_txt)
            if inicio is None or fim is None:
                raise ValueError("Periodo invalido")
            return inicio, fim

        parsed = parse_date(periodo)
        if parsed is None:
            raise ValueError("Periodo invalido")
        return parsed, parsed

    @staticmethod
    def _infer_origem(filepath: str, movimentacoes: list[dict[str, Any]]) -> str:
        nome = normalize_search_text(Path(filepath).name)
        if "camara" in nome:
            return "camara"
        if "saude" in nome:
            return "saude"
        if "consolidada" in nome:
            return "consolidada"
        if "admnistracao-direta" in nome or "administracao-direta" in nome:
            return "administracao_direta"
        if "prefeitura" in nome:
            return "prefeitura"

        for movimentacao in movimentacoes:
            unidade = normalize_search_text(movimentacao.get("unidade_gestora"))
            if "camara" in unidade:
                return "camara"
            if "saude" in unidade or "fumusa" in unidade:
                return "saude"

        return "prefeitura"

    @staticmethod
    def _txt(node, tag: str) -> str | None:
        if node is None:
            return None
        child = node.find(tag)
        if child is None or child.text is None:
            return None
        value = child.text.strip()
        return value or None
