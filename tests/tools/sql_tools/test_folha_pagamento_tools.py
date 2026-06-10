from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.folha_pagamento as folha_pagamento_tools
from database import session as session_manager
from database.session import _normalizar_texto
from database.models import (
    Base,
    Eleito,
    FolhaCargo,
    FolhaLotacao,
    FolhaPagamentoRegistro,
    FolhaServidor,
)


def _build_session():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def on_connect(conn, _):
        conn.create_function("normalizar", 1, _normalizar_texto)

    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return session_local()


def _snapshot(
    *,
    nome: str,
    cargo: str = "nao_informado",
    secretaria: str = "nao_informado",
    salario_base=None,
    competencia_referencia: date,
) -> FolhaServidor:
    return FolhaServidor(
        nome=nome,
        cargo=cargo,
        secretaria=secretaria,
        salario_base=salario_base,
        competencia_referencia=competencia_referencia,
    )


def test_busca_historico_de_pagamentos_serializa_contrato_leigo(monkeypatch) -> None:
    session = _build_session()

    folha_servidor_janeiro = _snapshot(
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
        salario_base=2500,
        competencia_referencia=date(2025, 1, 1),
    )
    folha_servidor_fevereiro = _snapshot(
        nome="Maria da Silva",
        cargo="Enfermeira",
        secretaria="Secretaria de Saude",
        salario_base=2600,
        competencia_referencia=date(2025, 2, 1),
    )
    cargo = FolhaCargo(nome="Enfermeira")
    lotacao = FolhaLotacao(nome="UPA Central")

    session.add_all([folha_servidor_janeiro, folha_servidor_fevereiro, cargo, lotacao])
    session.flush()

    session.add_all(
        [
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=2,
                competencia_mes_nome="Fevereiro",
                servidor=folha_servidor_fevereiro,
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
                servidor=folha_servidor_janeiro,
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
        " Maria da Silva ",
        limite=5,
        max_meses=2,
    )

    assert resultado["query"] == "Maria da Silva"
    assert resultado["total"] == 1
    assert resultado["resultados"][0]["folha_servidor_id"] == folha_servidor_fevereiro.id
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
    assert resultado["resultados"][0]["nota"].endswith("Historico limitado aos ultimos 2 meses de pagamento.")
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


def test_busca_historico_de_pagamentos_aceita_termos_nao_contiguos(
    monkeypatch,
) -> None:
    session = _build_session()

    folha_servidor = _snapshot(
        nome="Ronaldo Gaspar Ribeiro",
        cargo="Motorista",
        secretaria="Secretaria de Transportes",
        salario_base=2200,
        competencia_referencia=date(2025, 3, 1),
    )
    cargo = FolhaCargo(nome="Motorista")
    lotacao = FolhaLotacao(nome="Transportes")

    session.add_all([folha_servidor, cargo, lotacao])
    session.flush()
    session.add(
        FolhaPagamentoRegistro(
            competencia_ano=2025,
            competencia_mes_num=3,
            competencia_mes_nome="Marco",
            servidor=folha_servidor,
            cargo=cargo,
            lotacao=lotacao,
            salario_base=2200,
            proventos=2200,
            vantagens=0,
            vencimentos_totais=2200,
            descontos=200,
            liquido=2000,
        )
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Ronaldo Ribeiro")

    assert resultado["query"] == "Ronaldo Ribeiro"
    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == "Ronaldo Gaspar Ribeiro"

    session.close()


def test_busca_historico_de_pagamentos_ignora_diferenca_de_acentos(
    monkeypatch,
) -> None:
    session = _build_session()

    folha_servidor = _snapshot(
        nome="Wellington Francelli Estevao Rodrigues Roque",
        cargo="Prefeito Municipal",
        secretaria="Governo",
        salario_base=22614.44,
        competencia_referencia=date(2025, 12, 1),
    )
    cargo = FolhaCargo(nome="Prefeito Municipal")
    lotacao = FolhaLotacao(nome="M. SEC. GOV-SUB.PREF")

    session.add_all([folha_servidor, cargo, lotacao])
    session.flush()
    session.add(
        FolhaPagamentoRegistro(
            competencia_ano=2025,
            competencia_mes_num=12,
            competencia_mes_nome="Dezembro",
            servidor=folha_servidor,
            cargo=cargo,
            lotacao=lotacao,
            salario_base=22614.44,
            proventos=22614.44,
            vantagens=0,
            vencimentos_totais=22614.44,
            descontos=4500,
            liquido=18114.44,
        )
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor(
        "Wellington Francelli Estevão Rodrigues Roque"
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == ("Wellington Francelli Estevao Rodrigues Roque")
    assert resultado["resultados"][0]["cargo_atual"] == "Prefeito Municipal"
    assert resultado["resultados"][0]["pagamentos"][0]["salario_base"] == 22614.44

    session.close()


def test_busca_historico_de_pagamentos_resolve_cargo_politico_automaticamente(
    monkeypatch,
) -> None:
    session = _build_session()

    session.add(
        Eleito(
            tipo_politico="prefeito",
            municipio="Arcos",
            estado="MG",
            nome_completo="Wellington Francelli Estevão Rodrigues Roque",
            mandato_inicio=2025,
            mandato_fim=2028,
            mandato_status="em exercício",
        )
    )

    folha_servidor = _snapshot(
        nome="Wellington Francelli Estevao Rodrigues Roque",
        cargo="Prefeito Municipal",
        secretaria="Governo",
        salario_base=22614.44,
        competencia_referencia=date(2025, 12, 1),
    )
    cargo = FolhaCargo(nome="Prefeito Municipal")
    lotacao = FolhaLotacao(nome="Gabinete do Prefeito")

    session.add_all([folha_servidor, cargo, lotacao])
    session.flush()
    session.add(
        FolhaPagamentoRegistro(
            competencia_ano=2025,
            competencia_mes_num=12,
            competencia_mes_nome="Dezembro",
            servidor=folha_servidor,
            cargo=cargo,
            lotacao=lotacao,
            salario_base=22614.44,
            proventos=22614.44,
            vantagens=0,
            vencimentos_totais=22614.44,
            descontos=4500,
            liquido=18114.44,
        )
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("do prefeito")

    assert resultado["query"] == "do prefeito"
    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == ("Wellington Francelli Estevao Rodrigues Roque")
    assert resultado["resultados"][0]["cargo_atual"] == "Prefeito Municipal"
    assert resultado["resultados"][0]["pagamentos"][0]["salario_base"] == 22614.44

    session.close()


def test_busca_historico_de_pagamentos_desambigua_multiplos_candidatos(
    monkeypatch,
) -> None:
    session = _build_session()

    primeiro = _snapshot(
        nome="Ronaldo Gaspar Ribeiro",
        cargo="Motorista",
        secretaria="Secretaria de Transportes",
        salario_base=2200,
        competencia_referencia=date(2025, 3, 1),
    )
    segundo = _snapshot(
        nome="Ronaldo Ribeiro Silva",
        cargo="Auxiliar Administrativo",
        secretaria="Secretaria de Saude",
        salario_base=2500,
        competencia_referencia=date(2025, 4, 1),
    )
    cargo_primeiro = FolhaCargo(nome="Motorista")
    cargo_segundo = FolhaCargo(nome="Auxiliar Administrativo")
    lotacao_primeira = FolhaLotacao(nome="Transportes")
    lotacao_segunda = FolhaLotacao(nome="UPA Central")

    session.add_all(
        [
            primeiro,
            segundo,
            cargo_primeiro,
            cargo_segundo,
            lotacao_primeira,
            lotacao_segunda,
        ]
    )
    session.flush()
    session.add_all(
        [
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=3,
                competencia_mes_nome="Marco",
                servidor=primeiro,
                cargo=cargo_primeiro,
                lotacao=lotacao_primeira,
                salario_base=2200,
                proventos=2200,
                vantagens=0,
                vencimentos_totais=2200,
                descontos=200,
                liquido=2000,
            ),
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=4,
                competencia_mes_nome="Abril",
                servidor=segundo,
                cargo=cargo_segundo,
                lotacao=lotacao_segunda,
                salario_base=2500,
                proventos=2500,
                vantagens=150,
                vencimentos_totais=2650,
                descontos=300,
                liquido=2350,
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Ronaldo Ribeiro")

    assert resultado["query"] == "Ronaldo Ribeiro"
    assert resultado["total"] == 2
    assert resultado["resultados"] == []
    assert resultado["candidatos"] == [
        {
            "folha_servidor_id": primeiro.id,
            "nome": "Ronaldo Gaspar Ribeiro",
            "cargo_atual": "Motorista",
            "secretaria_atual": "Secretaria de Transportes",
            "setor_atual": "Transportes",
            "mes_de_referencia_do_servidor": "2025-03-01",
        },
        {
            "folha_servidor_id": segundo.id,
            "nome": "Ronaldo Ribeiro Silva",
            "cargo_atual": "Auxiliar Administrativo",
            "secretaria_atual": "Secretaria de Saude",
            "setor_atual": "UPA Central",
            "mes_de_referencia_do_servidor": "2025-04-01",
        },
    ]
    assert "mais de um servidor" in resultado["mensagem"]
    assert "folha_servidor_id" in resultado["mensagem"]

    session.close()


def test_busca_historico_de_pagamentos_aceita_folha_servidor_id_para_desempate(
    monkeypatch,
) -> None:
    session = _build_session()

    folha_servidor_janeiro = _snapshot(
        nome="Ronaldo Gaspar Ribeiro",
        cargo="Motorista",
        secretaria="Secretaria de Transportes",
        salario_base=2100,
        competencia_referencia=date(2025, 1, 1),
    )
    folha_servidor_marco = _snapshot(
        nome="Ronaldo Gaspar Ribeiro",
        cargo="Motorista",
        secretaria="Secretaria de Transportes",
        salario_base=2200,
        competencia_referencia=date(2025, 3, 1),
    )
    cargo = FolhaCargo(nome="Motorista")
    lotacao = FolhaLotacao(nome="Transportes")

    session.add_all([folha_servidor_janeiro, folha_servidor_marco, cargo, lotacao])
    session.flush()
    session.add_all(
        [
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=1,
                competencia_mes_nome="Janeiro",
                servidor=folha_servidor_janeiro,
                cargo=cargo,
                lotacao=lotacao,
                salario_base=2100,
                proventos=2100,
                vantagens=0,
                vencimentos_totais=2100,
                descontos=180,
                liquido=1920,
            ),
            FolhaPagamentoRegistro(
                competencia_ano=2025,
                competencia_mes_num=3,
                competencia_mes_nome="Marco",
                servidor=folha_servidor_marco,
                cargo=cargo,
                lotacao=lotacao,
                salario_base=2200,
                proventos=2200,
                vantagens=0,
                vencimentos_totais=2200,
                descontos=200,
                liquido=2000,
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor(
        folha_servidor_id=folha_servidor_marco.id
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["folha_servidor_id"] == folha_servidor_marco.id
    assert resultado["resultados"][0]["nome"] == "Ronaldo Gaspar Ribeiro"
    assert resultado["resultados"][0]["cargo_atual"] == "Motorista"
    assert resultado["resultados"][0]["total_meses_considerados"] == 2

    session.close()


def test_busca_historico_de_pagamentos_retorna_mensagem_para_nome_vazio() -> None:
    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("   ")

    assert resultado["total"] == 0
    assert resultado["mensagem"] == (
        "Informe um nome de servidor ou selecione um `folha_servidor_id` para realizar a busca."
    )


def test_busca_historico_de_pagamentos_exige_nome_suficiente() -> None:
    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Ronaldo")

    assert resultado["query"] == "Ronaldo"
    assert resultado["total"] == 0
    assert resultado["resultados"] == []
    assert resultado["mensagem"] == (
        "Informação insuficiente para consultar salário individual. "
        "Informe o nome completo ou pelo menos primeiro nome e outro sobrenome "
        "do servidor."
    )


def test_busca_historico_de_pagamentos_avisa_quando_base_de_folha_esta_vazia(
    monkeypatch,
) -> None:
    session = _build_session()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Jose Silva")

    assert resultado["query"] == "Jose Silva"
    assert resultado["total"] == 0
    assert resultado["mensagem"] == (
        "A base local de folha de pagamento esta vazia. Importe os XMLs de folha antes de consultar salarios."
    )

    session.close()


def test_busca_historico_de_pagamentos_retorna_sugestao_sem_resultados(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        _snapshot(
            nome="Maria da Silva",
            cargo="Enfermeira",
            secretaria="Secretaria de Saude",
            salario_base=2500,
            competencia_referencia=date(2025, 2, 1),
        )
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)

    resultado = folha_pagamento_tools.buscar_historico_de_pagamentos_do_servidor("Jose Silva")

    assert resultado["query"] == "Jose Silva"
    assert resultado["total"] == 0
    assert resultado["sugestao"] == (
        "Nenhum servidor encontrado com 'Jose Silva'. "
        "Confira a grafia ou tente uma combinação menos ambígua do nome, "
        "como primeiro nome e outro sobrenome."
    )

    session.close()
