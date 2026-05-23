from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.servidores as servidores_tools
from database.models import Base, Servidor


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


def test_busca_servidores_por_nome_serializa_resultados(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Maria da Silva",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2500,
                competencia_referencia=date(2025, 1, 1),
            ),
            Servidor(
                nome="Mariana Souza",
                cargo="Medica",
                secretaria="Secretaria de Saude",
                salario_base=4200,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.buscar_servidores_por_nome(" Maria ", limite=1)

    assert resultado["query"] == "Maria"
    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == "Maria da Silva"
    assert resultado["resultados"][0]["salario_base"] == 2500.0
    assert resultado["resultados"][0]["competencia_referencia"] == "2025-01-01"

    session.close()


def test_busca_servidores_por_periodo_aceita_formatos_de_data(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Carlos Pereira",
                cargo="Professor",
                secretaria="Secretaria de Educacao",
                salario_base=3100,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Joana Lima",
                cargo="Assistente",
                secretaria="Secretaria de Obras",
                salario_base=1800,
                competencia_referencia=date(2025, 3, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.buscar_servidores_por_competencia_no_periodo(
        "01/02/2025",
        "2025-03-01",
        limite=10,
    )

    assert resultado["total"] == 2
    assert resultado["data_inicio"] == "2025-02-01"
    assert resultado["data_fim"] == "2025-03-01"
    assert [item["nome"] for item in resultado["resultados"]] == [
        "Carlos Pereira",
        "Joana Lima",
    ]

    session.close()


def test_busca_servidores_por_nome_retorna_mensagem_para_termo_vazio() -> None:
    resultado = servidores_tools.buscar_servidores_por_nome("   ")

    assert resultado["total"] == 0
    assert resultado["mensagem"] == "Informe um nome de servidor para realizar a busca."
