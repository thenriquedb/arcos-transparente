from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.servidores as servidores_tools
from database import session as session_manager
from database.session import _normalizar_texto
from database.models import Base, FolhaServidor


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


def _patch_session(monkeypatch, session) -> None:
    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)


def Servidor(
    *,
    nome: str,
    cargo: str,
    secretaria: str,
    salario_base,
    competencia_referencia: date,
) -> FolhaServidor:
    return FolhaServidor(
        nome=nome,
        cargo=cargo,
        secretaria=secretaria,
        salario_base=salario_base,
        competencia_referencia=competencia_referencia,
    )


def test_consultar_servidores_aplica_mes_mais_recente_por_padrao(monkeypatch) -> None:
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
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        filtros={"secretaria": "saude"},
        ordenar_por="nome",
        ordem="asc",
    )

    assert resultado["total"] == 2
    assert [item["nome"] for item in resultado["resultados"]] == [
        "Ana Clara",
        "Bruno Costa",
    ]
    assert resultado["metadata"]["mes_de_referencia_considerado"] == "2025-02-01"
    assert resultado["metadata"]["mes_de_referencia_padrao_aplicado"] is True

    session.close()


def test_consultar_servidores_busca_nome_por_multiplos_termos(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Maria da Silva",
                cargo="Auxiliar",
                secretaria="Secretaria de Educacao",
                salario_base=1800,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Maria Eduarda",
                cargo="Auxiliar",
                secretaria="Secretaria de Educacao",
                salario_base=1700,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Joao Silva",
                cargo="Motorista",
                secretaria="Secretaria de Obras",
                salario_base=2200,
                competencia_referencia=date(2025, 2, 1),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        filtros={"nome": "Maria Silva"},
        ordenar_por="nome",
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == "Maria da Silva"

    session.close()


def test_consultar_servidores_ignora_diferenca_de_acentos_no_nome(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        Servidor(
            nome="Wellington Francelli Estevao Rodrigues Roque",
            cargo="Prefeito Municipal",
            secretaria="Governo",
            salario_base=22614.44,
            competencia_referencia=date(2025, 12, 1),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        filtros={"nome": "Wellington Francelli Estevão Rodrigues Roque"},
        ordenar_por="nome",
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome"] == (
        "Wellington Francelli Estevao Rodrigues Roque"
    )
    assert resultado["resultados"][0]["cargo"] == "Prefeito Municipal"

    session.close()


def test_consultar_servidores_filtra_por_cargo(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Servidor(
                nome="Bruno Costa",
                cargo="Medico Clinico",
                secretaria="Secretaria de Saude",
                salario_base=5200,
                competencia_referencia=date(2025, 2, 1),
            ),
            Servidor(
                nome="Beatriz Lima",
                cargo="Medica Pediatra",
                secretaria="Secretaria de Saude",
                salario_base=6100,
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
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        filtros={"cargo": "medic"},
        ordenar_por="nome",
    )

    assert resultado["total"] == 2
    assert [item["nome"] for item in resultado["resultados"]] == [
        "Beatriz Lima",
        "Bruno Costa",
    ]

    session.close()


def test_consultar_servidores_suporta_top_salarios_com_projecao(monkeypatch) -> None:
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
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        ordenar_por="salario_base",
        ordem="desc",
        limite=2,
        campos=["nome", "salario_base", "cargo", "secretaria"],
    )

    assert resultado["total"] == 3
    assert resultado["mensagem"] == "Mostrando 2 de 3 registros encontrados."
    assert resultado["resultados"] == [
        {
            "nome": "Carla Sousa",
            "salario_base": 10400.0,
            "cargo": "Procuradora",
            "secretaria": "Procuradoria",
        },
        {
            "nome": "Bruno Costa",
            "salario_base": 9100.0,
            "cargo": "Medico",
            "secretaria": "Secretaria de Saude",
        },
    ]

    session.close()


def test_consultar_servidores_filtra_por_periodo_de_mes_de_referencia(
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
                competencia_referencia=date(2025, 3, 1),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.consultar_servidores(
        filtros={
            "mes_de_referencia_inicio": "01/01/2025",
            "mes_de_referencia_fim": "28/02/2025",
        },
        ordenar_por="mes_de_referencia",
        ordem="asc",
        campos=["nome", "mes_de_referencia"],
    )

    assert resultado["total"] == 2
    assert resultado["metadata"]["mes_de_referencia_considerado"] is None
    assert resultado["metadata"]["mes_de_referencia_padrao_aplicado"] is False
    assert resultado["metadata"]["filtros_aplicados"] == {
        "mes_de_referencia_inicio": "2025-01-01",
        "mes_de_referencia_fim": "2025-02-28",
    }
    assert resultado["resultados"] == [
        {"nome": "Ana Clara", "mes_de_referencia": "2025-01-01"},
        {"nome": "Bruno Costa", "mes_de_referencia": "2025-02-01"},
    ]

    session.close()


@pytest.mark.parametrize(
    ("filtros", "mensagem_esperada"),
    [
        (
            {
                "mes_de_referencia": "01/02/2025",
                "mes_de_referencia_inicio": "01/01/2025",
                "mes_de_referencia_fim": "28/02/2025",
            },
            "mes_de_referencia nao pode ser usado junto com",
        ),
        (
            {"mes_de_referencia_inicio": "01/01/2025"},
            "mes_de_referencia_inicio e mes_de_referencia_fim devem ser informados juntos",
        ),
        (
            {
                "mes_de_referencia_inicio": "01/03/2025",
                "mes_de_referencia_fim": "01/02/2025",
            },
            "data_inicio deve ser menor ou igual a data_fim",
        ),
    ],
)
def test_consultar_servidores_valida_combinacoes_invalidas_de_periodo(
    filtros,
    mensagem_esperada,
) -> None:
    resultado = servidores_tools.consultar_servidores(filtros=filtros)

    assert resultado["total"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]
    assert mensagem_esperada in resultado["mensagem"]


def test_agregar_servidores_conta_sem_agrupar(monkeypatch) -> None:
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
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.agregar_servidores(
        filtros={"secretaria": "saude"},
        metrica="contagem",
    )

    assert resultado["total_grupos"] == 0
    assert resultado["valor_total"] == 2
    assert resultado["metadata"]["metrica"] == "contagem"

    session.close()


def test_agregar_servidores_ranqueia_secretarias(monkeypatch) -> None:
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
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.agregar_servidores(
        agrupar_por="secretaria",
        metrica="contagem",
        ordenar_por="metrica",
        ordem="desc",
        limite=2,
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"secretaria": "Secretaria de Educacao", "contagem": 3},
        {"secretaria": "Secretaria de Saude", "contagem": 2},
    ]

    session.close()


def test_agregar_servidores_retorna_lider_com_limite_1(monkeypatch) -> None:
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
    _patch_session(monkeypatch, session)

    resultado = servidores_tools.agregar_servidores(
        agrupar_por="secretaria",
        metrica="contagem",
        ordenar_por="metrica",
        ordem="desc",
        limite=1,
    )

    assert resultado["total_grupos"] == 2
    assert resultado["mensagem"] == "Mostrando 1 de 2 grupos encontrados."
    assert resultado["resultados"] == [
        {"secretaria": "Secretaria de Educacao", "contagem": 3},
    ]

    session.close()


def test_agregar_servidores_valida_combinacao_invalida() -> None:
    resultado = servidores_tools.agregar_servidores(
        agrupar_por="secretaria",
        ordenar_por="nome",
    )

    assert resultado["total_grupos"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]
