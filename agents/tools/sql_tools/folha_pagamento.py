"""Tools SQL para consultas de folha e servidores."""

from __future__ import annotations
from datetime import date

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from shared.utils.decimal_to_float import decimal_to_float
from database.models import FolhaPagamentoRegistro, FolhaServidor
from database.session import get_session


def busca_folha_pagamento_do_servidor(
    nome: str,
    limite: int = 10,
    max_pagamentos: int = 24,
) -> dict[str, Any]:
    """
    Busca um servidor público pelo nome e retorna seu histórico de pagamentos.

    Use quando o usuário perguntar sobre um servidor específico pelo nome.
    Exemplos:
    - 'quanto João Silva recebeu em 2024?'
    - 'qual o salário de Maria Souza?'
    - 'quais cargos Pedro Oliveira já ocupou?'
    - 'quanto foi pago a José no último ano?'

    Retorna: cargo atual, lotação, histórico de salários, proventos,
    descontos e valor líquido por competência.

    NÃO use para perguntas sem nome específico como 'quais servidores
    ganham mais de R$ 10 mil' ou 'quais cargos existem na prefeitura'.

    Args:
        nome: Nome ou parte do nome do servidor.
        limite: Número máximo de resultados (padrão 10, máximo 50).

    Returns:
        dict com 'total' e lista de 'resultados' contendo id, nome,
        cargo, secretaria, salario_base e referencia cadastral mais recente.
    """
    limite = max(1, min(limite, 50))
    max_pagamentos = max(1, min(max_pagamentos, 48))
    termo = nome.strip()

    if not termo:
        return {
            "query": nome,
            "total": 0,
            "resultados": [],
            "mensagem": "Informe um nome de servidor para realizar a busca.",
        }

    termo_normalizado = termo.lower()

    with get_session() as session:
        servidores = (
            session.execute(
                select(FolhaServidor)
                .options(
                    joinedload(FolhaServidor.servidor_canonico),
                    joinedload(FolhaServidor.pagamentos).joinedload(
                        FolhaPagamentoRegistro.cargo
                    ),
                    joinedload(FolhaServidor.pagamentos).joinedload(
                        FolhaPagamentoRegistro.lotacao
                    ),
                )
                .where(func.lower(FolhaServidor.nome).like(f"%{termo_normalizado}%"))
                .order_by(FolhaServidor.nome.asc())
                .limit(limite)
            )
            .unique()
            .scalars()
            .all()
        )

        if not servidores:
            return {
                "query": termo,
                "total": 0,
                "resultados": [],
                "sugestao": (
                    f"Nenhum servidor encontrado com '{termo}'. "
                    "Tente buscar por partes do nome, ex: só o sobrenome."
                ),
            }

        resultados = [
            _serializar_servidor(servidor, max_pagamentos) for servidor in servidores
        ]

        return {
            "query": termo,
            "total": len(resultados),
            "resultados": resultados,
        }


def _serializar_servidor(
    servidor: FolhaServidor,
    max_pagamentos: int,
) -> dict[str, Any]:
    pagamentos = sorted(
        servidor.pagamentos,
        key=lambda registro: (
            registro.competencia_ano,
            registro.competencia_mes_num,
        ),
        reverse=True,
    )
    pagamentos_limitados = pagamentos[:max_pagamentos]
    pagamento_recente = pagamentos_limitados[0] if pagamentos_limitados else None

    return {
        "folha_servidor_id": servidor.id,
        "nome": servidor.nome,
        "cargo_atual": (
            pagamento_recente.cargo.nome
            if pagamento_recente and pagamento_recente.cargo
            else None
        ),
        "lotacao_atual": (
            pagamento_recente.lotacao.nome
            if pagamento_recente and pagamento_recente.lotacao
            else None
        ),
        "competencia_referencia_servidor": (
            servidor.servidor_canonico.competencia_referencia.isoformat()
            if servidor.servidor_canonico
            and servidor.servidor_canonico.competencia_referencia
            else None
        ),
        "total_pagamentos_considerados": len(pagamentos_limitados),
        "pagamentos": [
            {
                "competencia_ano": registro.competencia_ano,
                "competencia_mes_num": registro.competencia_mes_num,
                "competencia_mes_nome": registro.competencia_mes_nome,
                "cargo": registro.cargo.nome if registro.cargo else None,
                "lotacao": registro.lotacao.nome if registro.lotacao else None,
                "salario_base": decimal_to_float(registro.salario_base),
                "proventos": decimal_to_float(registro.proventos),
                "vantagens": decimal_to_float(registro.vantagens),
                "vencimentos_totais": decimal_to_float(registro.vencimentos_totais),
                "descontos": decimal_to_float(registro.descontos),
                "liquido": decimal_to_float(registro.liquido),
            }
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
            f"Histórico limitado aos últimos {max_pagamentos} meses."
        ),
    }
