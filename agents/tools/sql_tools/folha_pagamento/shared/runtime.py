"""Utilitarios compartilhados das tools de folha."""

from __future__ import annotations

from datetime import date

from database.models import FolhaPagamentoRegistro, FolhaServidor
from shared.utils.decimal_to_float import decimal_to_float

from .responses import (
    FolhaServidorCandidato,
    HistoricoPagamentosServidorItem,
    HistoricoPagamentosServidorResponse,
    PagamentoMensalItem,
)


_PLACEHOLDER = "nao_informado"


def resposta_sem_resultados(
    *,
    query: str | None = None,
    total: int = 0,
    candidatos: list[dict[str, object]] | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, object]:
    return HistoricoPagamentosServidorResponse(
        query=query,
        total=total,
        resultados=[],
        candidatos=candidatos or [],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")


def serializar_servidor(
    servidores: list[FolhaServidor],
    max_meses: int,
) -> dict[str, object]:
    representante = _representante(servidores)
    pagamentos = _pagamentos_ordenados(servidores)
    pagamentos_limitados = pagamentos[:max_meses]
    pagamento_recente = pagamentos_limitados[0] if pagamentos_limitados else None

    payload = HistoricoPagamentosServidorItem.model_validate(
        {
            "folha_servidor_id": representante.id,
            "nome": representante.nome,
            "cargo_atual": _cargo_snapshot(representante, pagamento_recente),
            "setor_atual": (
                pagamento_recente.lotacao.nome
                if pagamento_recente and pagamento_recente.lotacao
                else _nullable_snapshot_text(representante.secretaria)
            ),
            "mes_de_referencia_do_servidor": representante.competencia_referencia,
            "total_meses_considerados": len(pagamentos_limitados),
            "pagamentos": [
                PagamentoMensalItem(
                    ano=registro.competencia_ano,
                    mes_num=registro.competencia_mes_num,
                    mes_nome=registro.competencia_mes_nome,
                    cargo=registro.cargo.nome if registro.cargo else None,
                    setor=registro.lotacao.nome if registro.lotacao else None,
                    salario_base=decimal_to_float(registro.salario_base),
                    ganhos=decimal_to_float(registro.proventos),
                    adicionais=decimal_to_float(registro.vantagens),
                    total_bruto=decimal_to_float(registro.vencimentos_totais),
                    descontos=decimal_to_float(registro.descontos),
                    valor_recebido=decimal_to_float(registro.liquido),
                )
                for registro in pagamentos_limitados
            ],
            "total_recebido": decimal_to_float(
                sum(registro.liquido for registro in pagamentos_limitados if registro.liquido is not None)
            ),
            "nota": (
                f"Dados consultados em {date.today().isoformat()}. "
                f"Historico limitado aos ultimos {max_meses} meses de pagamento."
            ),
        }
    )
    return payload.model_dump(mode="json")


def serializar_candidato_servidor(
    servidores: list[FolhaServidor],
) -> dict[str, object]:
    representante = _representante(servidores)
    pagamento_recente = _pagamentos_ordenados(servidores)[0] if servidores else None

    payload = FolhaServidorCandidato.model_validate(
        {
            "folha_servidor_id": representante.id,
            "nome": representante.nome,
            "cargo_atual": _cargo_snapshot(representante, pagamento_recente),
            "secretaria_atual": _nullable_snapshot_text(representante.secretaria),
            "setor_atual": (
                pagamento_recente.lotacao.nome
                if pagamento_recente and pagamento_recente.lotacao
                else _nullable_snapshot_text(representante.secretaria)
            ),
            "mes_de_referencia_do_servidor": representante.competencia_referencia,
        }
    )
    return payload.model_dump(mode="json")


def _representante(servidores: list[FolhaServidor]) -> FolhaServidor:
    return sorted(
        servidores,
        key=lambda servidor: (servidor.competencia_referencia, servidor.id),
        reverse=True,
    )[0]


def _pagamentos_ordenados(
    servidores: list[FolhaServidor],
) -> list[FolhaPagamentoRegistro]:
    pagamentos = [pagamento for servidor in servidores for pagamento in servidor.pagamentos]
    pagamentos.sort(
        key=lambda registro: (
            registro.competencia_ano,
            registro.competencia_mes_num,
            registro.id,
        ),
        reverse=True,
    )
    return pagamentos


def _cargo_snapshot(
    representante: FolhaServidor,
    pagamento_recente: FolhaPagamentoRegistro | None,
) -> str | None:
    if pagamento_recente and pagamento_recente.cargo:
        return pagamento_recente.cargo.nome
    return _nullable_snapshot_text(representante.cargo)


def _nullable_snapshot_text(value: str | None) -> str | None:
    if not value or value == _PLACEHOLDER:
        return None
    return value
