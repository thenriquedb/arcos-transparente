"""Utilitarios compartilhados das tools de folha."""

from __future__ import annotations

from datetime import date

from database.models import FolhaServidor
from shared.utils.decimal_to_float import decimal_to_float

from .responses import (
    HistoricoPagamentosServidorItem,
    HistoricoPagamentosServidorResponse,
    PagamentoMensalItem,
)


def resposta_sem_resultados(
    *,
    query: str | None = None,
    mensagem: str | None = None,
    sugestao: str | None = None,
) -> dict[str, object]:
    return HistoricoPagamentosServidorResponse(
        query=query,
        total=0,
        resultados=[],
        mensagem=mensagem,
        sugestao=sugestao,
    ).model_dump(mode="json")


def serializar_servidor(
    servidor: FolhaServidor,
    max_meses: int,
) -> dict[str, object]:
    pagamentos = sorted(
        servidor.pagamentos,
        key=lambda registro: (
            registro.competencia_ano,
            registro.competencia_mes_num,
        ),
        reverse=True,
    )
    pagamentos_limitados = pagamentos[:max_meses]
    pagamento_recente = pagamentos_limitados[0] if pagamentos_limitados else None

    payload = HistoricoPagamentosServidorItem.model_validate(
        {
            "folha_servidor_id": servidor.id,
            "nome": servidor.nome,
            "cargo_atual": (
                pagamento_recente.cargo.nome
                if pagamento_recente and pagamento_recente.cargo
                else None
            ),
            "setor_atual": (
                pagamento_recente.lotacao.nome
                if pagamento_recente and pagamento_recente.lotacao
                else None
            ),
            "mes_de_referencia_do_servidor": (
                servidor.servidor_canonico.competencia_referencia
                if servidor.servidor_canonico
                and servidor.servidor_canonico.competencia_referencia
                else None
            ),
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
                sum(
                    registro.liquido
                    for registro in pagamentos_limitados
                    if registro.liquido is not None
                )
            ),
            "nota": (
                f"Dados consultados em {date.today().isoformat()}. "
                f"Historico limitado aos ultimos {max_meses} meses de pagamento."
            ),
        }
    )
    return payload.model_dump(mode="json")
