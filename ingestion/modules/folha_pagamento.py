"""Modulo de ingestao adapter and loader for folha de pagamento."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, select

from database.models import (
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
)
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_bulk_adapter
from .discovery import discover_folha_pagamento_files
from .shared import apply_upsert_status, upsert_by_filters


def load_folha_pagamento(
    session,
    *,
    arquivos: list,
    parser,
    get_or_create_folha_dim,
    get_or_create_folha_servidor,
) -> LoadResult:
    """Load folha records into the dimensional model and snapshot table."""

    resultado = LoadResult()
    for arquivo in arquivos:
        registros = parser.parse(str(arquivo))
        for registro in registros:
            registro = sanitize_xml_payload(registro)
            try:
                with session.begin():
                    servidor = get_or_create_folha_servidor(
                        session=session,
                        nome=registro["nome_servidor"],
                        cargo=registro.get("cargo"),
                        lotacao=registro.get("lotacao"),
                        competencia_referencia=date(
                            registro["competencia_ano"],
                            registro["competencia_mes_num"],
                            1,
                        ),
                        salario_base=registro.get("salario_base"),
                    )
                    lotacao = get_or_create_folha_dim(
                        session,
                        FolhaLotacao,
                        registro.get("lotacao"),
                    )
                    cargo = get_or_create_folha_dim(
                        session,
                        FolhaCargo,
                        registro.get("cargo"),
                    )
                    payload = {
                        "competencia_ano": registro["competencia_ano"],
                        "competencia_mes_num": registro["competencia_mes_num"],
                        "competencia_mes_nome": registro["competencia_mes_nome"],
                        "servidor_id": servidor.id,
                        "lotacao_id": lotacao.id if lotacao else None,
                        "cargo_id": cargo.id if cargo else None,
                        "salario_base": registro.get("salario_base"),
                        "proventos": registro.get("proventos"),
                        "vantagens": registro.get("vantagens"),
                        "vencimentos_totais": registro.get("vencimentos_totais"),
                        "descontos": registro.get("descontos"),
                        "liquido": registro.get("liquido"),
                    }
                    _, status = upsert_by_filters(
                        session,
                        FolhaPagamentoRegistro,
                        filters=[
                            FolhaPagamentoRegistro.competencia_ano
                            == payload["competencia_ano"],
                            FolhaPagamentoRegistro.competencia_mes_nome
                            == payload["competencia_mes_nome"],
                            FolhaPagamentoRegistro.servidor_id
                            == payload["servidor_id"],
                            FolhaPagamentoRegistro.cargo_id == payload["cargo_id"],
                            FolhaPagamentoRegistro.lotacao_id == payload["lotacao_id"],
                        ],
                        payload=payload,
                    )
                    apply_upsert_status(resultado, status)
            except Exception:
                session.rollback()
                resultado.erros += 1
    return resultado


def get_or_create_folha_dim(session, model, nome: str | None):
    """Find or create one textual folha dimension entry."""

    nome = sanitize_xml_payload(nome)
    if not nome:
        return None

    existente = session.execute(
        select(model).where(model.nome == nome)
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    instancia = model(nome=nome)
    session.add(instancia)
    session.flush()
    return instancia


def get_or_create_folha_servidor(
    session,
    *,
    nome: str,
    cargo: str | None,
    lotacao: str | None,
    competencia_referencia: date,
    salario_base,
) -> FolhaServidor:
    """Find or create the folha snapshot row keyed by competencia and lotacao."""

    nome = sanitize_xml_payload(nome)
    cargo = sanitize_xml_payload(cargo) or "nao_informado"
    lotacao = sanitize_xml_payload(lotacao) or "nao_informado"
    salario_base = sanitize_xml_payload(salario_base)

    existente = session.execute(
        select(FolhaServidor).where(
            and_(
                FolhaServidor.nome == nome,
                FolhaServidor.cargo == cargo,
                FolhaServidor.secretaria == lotacao,
                FolhaServidor.competencia_referencia == competencia_referencia,
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        if existente.salario_base != salario_base:
            existente.salario_base = salario_base
        return existente

    instancia = FolhaServidor(
        nome=nome,
        cargo=cargo,
        secretaria=lotacao,
        salario_base=salario_base,
        competencia_referencia=competencia_referencia,
    )
    session.add(instancia)
    session.flush()
    return instancia


ADAPTER = build_pipeline_bulk_adapter(
    "folha_pagamento",
    discover_files=discover_folha_pagamento_files,
    pipeline_method_name="_load_folha_pagamento",
)
