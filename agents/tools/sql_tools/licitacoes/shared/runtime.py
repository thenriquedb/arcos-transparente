"""Utilitarios compartilhados de serializacao das tools de licitacoes."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from database.models import InstrumentoContratual, Licitacao, MateriaInstrumento
from shared.utils.decimal_to_float import decimal_to_float


def _decimal_to_json(value: Decimal | None, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    return decimal_to_float(value)


def serializar_materia(materia: MateriaInstrumento) -> dict[str, Any]:
    return {
        "numero_lote": materia.numero_lote,
        "numero_item": materia.numero_item,
        "identificacao": materia.identificacao,
        "quantidade": _decimal_to_json(materia.quantidade),
        "valor_unitario": _decimal_to_json(materia.valor_unitario),
        "valor_total": _decimal_to_json(materia.valor_total),
    }


def serializar_instrumento(
    instrumento: InstrumentoContratual,
    *,
    max_itens: int,
) -> dict[str, Any]:
    materias = instrumento.materias[:max_itens]
    fornecedor_nome = instrumento.fornecedor.nome if instrumento.fornecedor else None
    return {
        "numero_instrumento": instrumento.numero_instrumento,
        "tipo_instrumento": instrumento.tipo_instrumento_contratual,
        "tipo_contrato": instrumento.tipo_contrato,
        "fornecedor": fornecedor_nome,
        "objeto": instrumento.objeto,
        "data_emissao": instrumento.data_emissao,
        "data_expiracao": instrumento.data_expiracao,
        "possui_aditivo": instrumento.possui_aditivo,
        "valor": _decimal_to_json(instrumento.valor_instrumento_contratual),
        "total_itens": len(instrumento.materias),
        "itens": [serializar_materia(materia) for materia in materias],
    }


def serializar_licitacao(
    licitacao: Licitacao,
    *,
    incluir_detalhes: bool = False,
    max_vencedores: int = 5,
    max_instrumentos: int = 5,
    max_itens: int = 10,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": licitacao.id,
        "numero": licitacao.numero,
        "modalidade": licitacao.modalidade,
        "objeto": licitacao.objeto,
        "valor_estimado": _decimal_to_json(licitacao.valor_estimado),
        "data_abertura": licitacao.data_abertura,
        "situacao": licitacao.situacao,
        "secretaria": licitacao.secretaria,
    }

    if not incluir_detalhes:
        return payload

    vencedores = licitacao.vencedores[:max_vencedores]
    instrumentos = licitacao.instrumentos_contratuais[:max_instrumentos]
    payload.update(
        {
            "total_vencedores": len(licitacao.vencedores),
            "vencedores": [
                {
                    "nome": vencedor.nome,
                    "cnpj_cpf": vencedor.cnpj_cpf,
                    "validade_proposta": vencedor.validade_proposta,
                }
                for vencedor in vencedores
            ],
            "total_instrumentos": len(licitacao.instrumentos_contratuais),
            "instrumentos": [serializar_instrumento(instrumento, max_itens=max_itens) for instrumento in instrumentos],
        }
    )
    return payload
