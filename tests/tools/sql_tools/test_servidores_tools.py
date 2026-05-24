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
    assert resultado["resultados"][0]["mes_de_referencia"] == "2025-01-01"
    assert "competencia_referencia" not in resultado["resultados"][0]

    session.close()


def test_busca_servidores_por_mes_de_referencia_no_periodo_aceita_formatos_de_data(
    monkeypatch,
) -> None:
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

    resultado = servidores_tools.buscar_servidores_por_mes_de_referencia_no_periodo(
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


def test_lista_maiores_salarios_ordena_do_maior_para_o_menor(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Alice Souza",
                cargo="Medica",
                secretaria="Secretaria de Saude",
                salario_base=8200,
                competencia_referencia=date(2025, 1, 1),
            ),
            Servidor(
                nome="Bruno Costa",
                cargo="Medico",
                secretaria="Secretaria de Saude",
                salario_base=9100,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Carla Sousa",
                cargo="Procuradora",
                secretaria="Procuradoria",
                salario_base=10400,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Daniel Lima",
                cargo="Engenheiro",
                secretaria="Secretaria de Obras",
                salario_base=7600,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.listar_maiores_salarios(limite=2)

    assert resultado["query"] == "maiores salarios"
    assert resultado["mes_de_referencia"] == "2025-02-01"
    assert resultado["total"] == 3
    assert resultado["mensagem"] == (
        "Mostrando 2 de 3 servidores com salario no mes mais recente com dados."
    )
    assert resultado["resultados"] == [
        {
            "id": 3,
            "nome": "Carla Sousa",
            "cargo": "Procuradora",
            "secretaria": "Procuradoria",
            "salario_base": 10400.0,
            "mes_de_referencia": "2025-02-01",
        },
        {
            "id": 2,
            "nome": "Bruno Costa",
            "cargo": "Medico",
            "secretaria": "Secretaria de Saude",
            "salario_base": 9100.0,
            "mes_de_referencia": "2025-02-01",
        },
    ]

    session.close()


def test_lista_servidores_da_secretaria_considera_competencia_mais_recente(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2400,
                competencia_referencia=date(2025, 1, 1),
            ),
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2500,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Bruno Costa",
                cargo="Medico",
                secretaria="Secretaria de Saude",
                salario_base=5200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Carla Sousa",
                cargo="Professora",
                secretaria="Secretaria de Educacao",
                salario_base=3200,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.listar_servidores_da_secretaria(" saude ", limite=1)

    assert resultado["query"] == "saude"
    assert resultado["mes_de_referencia"] == "2025-02-01"
    assert resultado["total"] == 2
    assert resultado["secretarias_correspondentes"] == ["Secretaria de Saude"]
    assert resultado["mensagem"] == (
        "Mostrando 1 de 2 servidores no mes mais recente com dados."
    )
    assert [item["nome"] for item in resultado["resultados"]] == ["Ana Clara"]
    assert resultado["resultados"][0]["salario_base"] == 2500.0
    assert resultado["resultados"][0]["mes_de_referencia"] == "2025-02-01"
    assert "competencia_referencia" not in resultado
    assert "competencia_referencia" not in resultado["resultados"][0]

    session.close()


def test_conta_servidores_por_secretaria_ignora_competencias_antigas(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2400,
                competencia_referencia=date(2025, 1, 1),
            ),
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2500,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Bruno Costa",
                cargo="Medico",
                secretaria="Secretaria de Saude",
                salario_base=5200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Carla Sousa",
                cargo="Professora",
                secretaria="Secretaria de Educacao",
                salario_base=3200,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.contar_servidores_por_secretaria("Saude")

    assert resultado["query"] == "Saude"
    assert resultado["mes_de_referencia"] == "2025-02-01"
    assert resultado["total_servidores"] == 2
    assert resultado["secretarias_correspondentes"] == ["Secretaria de Saude"]
    assert "competencia_referencia" not in resultado

    session.close()


def test_lista_secretarias_por_quantidade_de_servidores_retorna_ranking(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2500,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Bruno Costa",
                cargo="Medico",
                secretaria="Secretaria de Saude",
                salario_base=5200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Carla Sousa",
                cargo="Professora",
                secretaria="Secretaria de Educacao",
                salario_base=3200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Daniel Lima",
                cargo="Professor",
                secretaria="Secretaria de Educacao",
                salario_base=3300,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Elaine Rocha",
                cargo="Coordenadora",
                secretaria="Secretaria de Educacao",
                salario_base=4100,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.listar_secretarias_por_quantidade_de_servidores(
        limite=2
    )

    assert resultado["mes_de_referencia"] == "2025-02-01"
    assert resultado["total"] == 2
    assert resultado["resultados"] == [
        {"secretaria": "Secretaria de Educacao", "total_servidores": 3},
        {"secretaria": "Secretaria de Saude", "total_servidores": 2},
    ]
    assert "competencia_referencia" not in resultado

    session.close()


def test_busca_secretaria_com_mais_servidores_retorna_lider(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Ana Clara",
                cargo="Enfermeira",
                secretaria="Secretaria de Saude",
                salario_base=2500,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Carla Sousa",
                cargo="Professora",
                secretaria="Secretaria de Educacao",
                salario_base=3200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Daniel Lima",
                cargo="Professor",
                secretaria="Secretaria de Educacao",
                salario_base=3300,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()

    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(servidores_tools, "get_session", fake_get_session)

    resultado = servidores_tools.buscar_secretaria_com_mais_servidores()

    assert resultado == {
        "mes_de_referencia": "2025-02-01",
        "secretaria": "Secretaria de Educacao",
        "total_servidores": 2,
        "mensagem": None,
        "sugestao": None,
    }

    session.close()
