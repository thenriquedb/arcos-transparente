from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.folha_pagamento as folha_pagamento_tools
from database import session as session_manager
from database.models import (
    Base,
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
    Servidor,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return session_local()


def test_busca_historico_de_pagamentos_serializa_contrato_leigo(monkeypatch) -> None:
    session = _build_session()

    servidor_canonico = Servidor(
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
        salario_base=2500,
        competencia_referencia=date(2025, 2, 1),
    )
    folha_servidor = FolhaServidor(
        nome="Maria da Silva",
        servidor_canonico=servidor_canonico,
    )
    cargo = FolhaCargo(nome="Enfermeira")
    lotacao = FolhaLotacao(nome="UPA Central")

    session.add_all([servidor_canonico, folha_servidor, cargo, lotacao])
    session.flush()

    session.add_all(
        [
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=2,
                competencia_mes_nome="Fevereiro",
                servidor=folha_servidor,
                cargo=cargo,
                lotacao=lotacao,
                salario_base=2600,
                proventos=3100,
                vantagens=200,
                vencimentos_totais=3300,
                descontos=400,
                liquido=2900,
            ),
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=1,
                competencia_mes_nome="Janeiro",
                servidor=folha_servidor,
                cargo=cargo,
                lotacao=lotacao,
                salario_base=2500,
                proventos=3000,
                vantagens=150,
                vencimentos_totais=3150,
                descontos=350,
                liquido=2800,
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor(
        " Maria ",
        limite=5,
        max_meses=2,
    )

    assert resultado["query"] == "Maria"
    assert resultado["total"] == 1
    assert resultado["resultados"][0]["folha_servidor_id"] == folha_servidor.id
    assert resultado["resultados"][0]["nome"] == "Maria da Silva"
    assert resultado["resultados"][0]["cargo_atual"] == "Enfermeira"
    assert resultado["resultados"][0]["setor_atual"] == "UPA Central"
    assert resultado["resultados"][0]["mes_de_referencia_do_servidor"] == "2025-02-01"
    assert resultado["resultados"][0]["total_meses_considerados"] == 2
    assert resultado["resultados"][0]["total_recebido"] == 5700.0
    assert resultado["resultados"][0]["pagamentos"] == [
        {
            "ano": 2025,
            "mes_num": 2,
            "mes_nome": "Fevereiro",
            "cargo": "Enfermeira",
            "setor": "UPA Central",
            "salario_base": 2600.0,
            "ganhos": 3100.0,
            "adicionais": 200.0,
            "total_bruto": 3300.0,
            "descontos": 400.0,
            "valor_recebido": 2900.0,
        },
        {
            "ano": 2025,
            "mes_num": 1,
            "mes_nome": "Janeiro",
            "cargo": "Enfermeira",
            "setor": "UPA Central",
            "salario_base": 2500.0,
            "ganhos": 3000.0,
            "adicionais": 150.0,
            "total_bruto": 3150.0,
            "descontos": 350.0,
            "valor_recebido": 2800.0,
        },
    ]
    assert resultado["resultados"][0]["nota"].endswith(
        "Historico limitado aos ultimos 2 meses de pagamento."
    )
    assert "lotacao_atual" not in resultado["resultados"][0]
    assert "competencia_referencia_servidor" not in resultado["resultados"][0]
    assert "total_pagamentos_considerados" not in resultado["resultados"][0]
    assert "competencia_ano" not in resultado["resultados"][0]["pagamentos"][0]
    assert "competencia_mes_num" not in resultado["resultados"][0]["pagamentos"][0]
    assert "competencia_mes_nome" not in resultado["resultados"][0]["pagamentos"][0]
    assert "lotacao" not in resultado["resultados"][0]["pagamentos"][0]
    assert "proventos" not in resultado["resultados"][0]["pagamentos"][0]
    assert "vantagens" not in resultado["resultados"][0]["pagamentos"][0]
    assert "vencimentos_totais" not in resultado["resultados"][0]["pagamentos"][0]
    assert "liquido" not in resultado["resultados"][0]["pagamentos"][0]

    session.close()


def test_busca_historico_de_pagamentos_retorna_mensagem_para_nome_vazio() -> None:
    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("   ")

    assert resultado["total"] == 0
    assert resultado["mensagem"] == "Informe um nome de servidor para realizar a busca."


def test_busca_historico_de_pagamentos_retorna_sugestao_sem_resultados(
    monkeypatch,
) -> None:
    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Jose")

    assert resultado["query"] == "Jose"
    assert resultado["total"] == 0
    assert resultado["sugestao"] == (
        "Nenhum servidor encontrado com 'Jose'. "
        "Tente buscar por partes do nome, ex: só o sobrenome."
    )

    session.close()
