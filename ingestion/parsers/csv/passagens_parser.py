"""Parser CSV para relatorios consolidados de passagens."""

from __future__ import annotations

from .beneficiario_report import BeneficiarioReportCsvParser


class PassagensCsvParser(BeneficiarioReportCsvParser):
    """Converte CSVs de passagens em registros canonicos de despesa."""

    tipo_origem = "passagem"
    documento_prefix = "PASSAGEM"
    report_label = "passagens"
    default_categoria = "PASSAGENS"
    default_descricao = "Passagens"
    categoria_metadata_keys = ("tipo da transferencia", "tipo de despesa")
