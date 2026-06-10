"""Parser CSV para relatorios consolidados de diarias."""

from __future__ import annotations

from .beneficiario_report import BeneficiarioReportCsvParser


class DiariasCsvParser(BeneficiarioReportCsvParser):
    """Converte CSVs de diarias em registros canonicos de despesa."""

    tipo_origem = "diaria"
    documento_prefix = "DIARIA"
    report_label = "diarias"
    default_categoria = "DIARIAS"
    default_descricao = "Diarias"
