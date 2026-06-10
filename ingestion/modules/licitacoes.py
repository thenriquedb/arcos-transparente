"""Modulo de ingestao adapter and loader for licitacoes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import and_, select

from database.models import (
    Fornecedor,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    VencedorLicitacao,
)
from ingestion.loaders.sql_loader import LoadResult
from ingestion.parsers.xml.shared import sanitize_xml_payload

from .adapters import build_pipeline_file_loader_adapter
from .discovery import discover_licitacoes_files
from .shared import apply_upsert_status, upsert_by_filters


def load_licitacoes(
    session,
    registros: list[dict[str, Any]],
    *,
    get_or_create_fornecedor: Callable[..., Any],
    to_date: Callable[[Any], Any],
) -> LoadResult:
    """Load licitacoes and rebuild nested vencedores/instrumentos/materias."""

    resultado = LoadResult()
    for registro in registros:
        registro = sanitize_xml_payload(registro)
        try:
            with session.begin():
                registro_base = {
                    "numero": registro["numero"],
                    "modalidade": registro["modalidade"],
                    "objeto": registro["objeto"],
                    "valor_estimado": registro["valor_estimado"],
                    "data_abertura": to_date(registro["data_abertura"]),
                    "situacao": registro["situacao"],
                    "secretaria": registro["secretaria"],
                }
                licitacao, status = upsert_by_filters(
                    session,
                    Licitacao,
                    filters=[
                        Licitacao.numero == registro_base["numero"],
                        Licitacao.data_abertura == registro_base["data_abertura"],
                    ],
                    payload=registro_base,
                )
                apply_upsert_status(resultado, status)

                if status != "inserted":
                    session.query(VencedorLicitacao).filter(VencedorLicitacao.licitacao_id == licitacao.id).delete()
                    session.query(MateriaInstrumento).filter(
                        MateriaInstrumento.instrumento_id.in_(
                            select(InstrumentoContratual.id).where(InstrumentoContratual.licitacao_id == licitacao.id)
                        )
                    ).delete(synchronize_session=False)
                    session.query(InstrumentoContratual).filter(
                        InstrumentoContratual.licitacao_id == licitacao.id
                    ).delete()

                for vencedor in registro.get("vencedores", []):
                    fornecedor = get_or_create_fornecedor(
                        session=session,
                        cnpj_cpf=vencedor["cnpj_cpf"],
                        nome=vencedor["nome"],
                    )
                    session.add(
                        VencedorLicitacao(
                            licitacao_id=licitacao.id,
                            fornecedor_id=fornecedor.id if fornecedor else None,
                            cnpj_cpf=vencedor["cnpj_cpf"],
                            nome=vencedor["nome"],
                            validade_proposta=vencedor.get("validade_proposta"),
                        )
                    )

                for instrumento in registro.get("instrumentos_contratuais", []):
                    fornecedor = None
                    if instrumento.get("cnpj_fornecedor") and instrumento.get("nome_fornecedor"):
                        fornecedor = get_or_create_fornecedor(
                            session=session,
                            cnpj_cpf=instrumento["cnpj_fornecedor"],
                            nome=instrumento["nome_fornecedor"],
                        )

                    instrumento_model = InstrumentoContratual(
                        licitacao_id=licitacao.id,
                        fornecedor_id=fornecedor.id if fornecedor else None,
                        numero_licitatorio=instrumento.get("numero_licitatorio"),
                        unidade_gestora=instrumento.get("unidade_gestora"),
                        tipo_instrumento_contratual=instrumento.get("tipo_instrumento_contratual"),
                        numero_instrumento=instrumento.get("numero_instrumento"),
                        tipo_contrato=instrumento.get("tipo_contrato"),
                        objeto=instrumento.get("objeto"),
                        data_emissao=to_date(instrumento.get("data_emissao")),
                        data_expiracao=to_date(instrumento.get("data_expiracao")),
                        possui_aditivo=instrumento.get("possui_aditivo"),
                        valor_instrumento_contratual=instrumento.get("valor_instrumento_contratual"),
                    )
                    session.add(instrumento_model)
                    session.flush()

                    for materia in instrumento.get("materias", []):
                        session.add(
                            MateriaInstrumento(
                                instrumento_id=instrumento_model.id,
                                unidade_gestora=materia.get("unidade_gestora"),
                                numero_lote=materia.get("numero_lote"),
                                numero_item=materia.get("numero_item"),
                                identificacao=materia.get("identificacao"),
                                quantidade=materia.get("quantidade"),
                                valor_unitario=materia.get("valor_unitario"),
                                valor_total=materia.get("valor_total"),
                            )
                        )
        except Exception:
            session.rollback()
            resultado.erros += 1
    return resultado


ADAPTER = build_pipeline_file_loader_adapter(
    "licitacoes",
    discover_files=discover_licitacoes_files,
    parser_attr="licitacoes_parser",
    pipeline_method_name="_load_licitacoes",
)
