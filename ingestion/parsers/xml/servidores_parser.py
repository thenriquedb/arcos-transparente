"""Parser do JSON de relacao de servidores."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from pydantic import ValidationError

from ingestion.schemas.servidores import ServidorInSchema


class ServidoresParser:
    """Converte o JSON de servidores em lista de dicionarios validados."""

    def parse(self, filepath: str) -> list[dict[str, Any]]:
        """Le arquivo JSON e retorna registros normalizados com Pydantic."""
        with open(filepath, "r", encoding="utf-8") as fp:
            payload = json.load(fp)

        if not isinstance(payload, list):
            raise ValueError("JSON de servidores deve ser uma lista de objetos suportados")

        registros: list[dict[str, Any]] = []
        invalidos = 0

        for raw_row in payload:
            if not isinstance(raw_row, dict):
                invalidos += 1
                continue

            payload_raw = {
                "source_id": raw_row.get("id"),
                "competencia_referencia": raw_row.get("Competencia"),
                "nome": raw_row.get("Nome"),
                "cpf": raw_row.get("CPF"),
                "matricula": raw_row.get("Matricula"),
                "cargo_funcao": raw_row.get("CargoFuncao"),
                "fundamento_legal": raw_row.get("FundamentoLegal"),
                "lotacao": raw_row.get("Lotacao"),
                "situacao_funcional": raw_row.get("SituacaoFuncional"),
                "forma_contratacao_investidura": raw_row.get("FormaContratacaoInvestidura"),
                "data_admissao": raw_row.get("DataAdmissao"),
                "data_desligamento": raw_row.get("DataDesligamento"),
                "horario_trabalho": raw_row.get("HorarioTrabalho"),
                "carga_horaria": raw_row.get("CargaHoraria"),
                "local_origem_cedencia": raw_row.get("LocalOrigemCedencia"),
                "local_destino_cedencia": raw_row.get("LocalDestinoCedencia"),
                "onus_pagamento_cedencia": raw_row.get("OnusPagamentoCedencia"),
                "data_inicio_cessao": raw_row.get("DataInicioCessao"),
                "data_fim_cessao": raw_row.get("DataFimCessao"),
                "regime_aposentadoria": raw_row.get("RegimeAposentadoria"),
                "vinculo_empregaticio": raw_row.get("VinculoEmpregaticio"),
            }

            try:
                payload = ServidorInSchema.model_validate(payload_raw)
            except ValidationError:
                invalidos += 1
                continue

            registros.append(payload.model_dump(mode="python"))

        if invalidos:
            logger.info(f"Descartados {invalidos} registros invalidos de servidores em {filepath}")

        return registros
