"""Helpers SQL compartilhados para consultas amplas de licitacoes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import exists, func, select

from database.models import Licitacao, VencedorLicitacao
from shared.utils.decimal_to_float import decimal_to_float

from .filters import LicitacoesFiltroSchema
from .runtime import serializar_licitacao


def apply_licitacoes_filters(stmt, filtros: LicitacoesFiltroSchema):
    if filtros.data_abertura is not None:
        stmt = stmt.where(Licitacao.data_abertura == filtros.data_abertura)
    elif (
        filtros.data_abertura_inicio is not None
        and filtros.data_abertura_fim is not None
    ):
        stmt = stmt.where(
            Licitacao.data_abertura.between(
                filtros.data_abertura_inicio,
                filtros.data_abertura_fim,
            )
        )

    if filtros.numero:
        stmt = stmt.where(
            func.lower(Licitacao.numero).like(f"%{filtros.numero.lower()}%")
        )
    if filtros.modalidade:
        stmt = stmt.where(
            func.lower(Licitacao.modalidade).like(f"%{filtros.modalidade.lower()}%")
        )
    if filtros.secretaria:
        stmt = stmt.where(
            func.lower(Licitacao.secretaria).like(f"%{filtros.secretaria.lower()}%")
        )
    if filtros.situacao:
        stmt = stmt.where(
            func.lower(Licitacao.situacao).like(f"%{filtros.situacao.lower()}%")
        )
    if filtros.valor_estimado_min is not None:
        stmt = stmt.where(Licitacao.valor_estimado >= filtros.valor_estimado_min)
    if filtros.valor_estimado_max is not None:
        stmt = stmt.where(Licitacao.valor_estimado <= filtros.valor_estimado_max)
    if filtros.fornecedor:
        stmt = stmt.where(
            exists(
                select(VencedorLicitacao.id).where(
                    VencedorLicitacao.licitacao_id == Licitacao.id,
                    func.lower(VencedorLicitacao.nome).like(
                        f"%{filtros.fornecedor.lower()}%"
                    ),
                )
            )
        )
    if filtros.cnpj_cpf:
        stmt = stmt.where(
            exists(
                select(VencedorLicitacao.id).where(
                    VencedorLicitacao.licitacao_id == Licitacao.id,
                    VencedorLicitacao.cnpj_cpf.like(f"%{filtros.cnpj_cpf}%"),
                )
            )
        )
    return stmt


def project_licitacao_fields(
    licitacao: Licitacao,
    campos: list[str],
    *,
    incluir_detalhes: bool,
    max_vencedores: int,
    max_instrumentos: int,
    max_itens: int,
) -> dict[str, Any]:
    serialized = serializar_licitacao(
        licitacao,
        incluir_detalhes=incluir_detalhes,
        max_vencedores=max_vencedores,
        max_instrumentos=max_instrumentos,
        max_itens=max_itens,
    )
    if not campos:
        return serialized

    projected = {campo: serialized[campo] for campo in campos}
    if incluir_detalhes:
        for detail_key in (
            "total_vencedores",
            "vencedores",
            "total_instrumentos",
            "instrumentos",
        ):
            projected[detail_key] = serialized[detail_key]
    return projected


def decimal_or_int_to_json(value: Decimal | int | None) -> float | int | None:
    if isinstance(value, Decimal):
        return decimal_to_float(value)
    return value
