from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.eleitos as eleitos_tools
from database import session as session_manager
from database.models import Base, Eleito


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


def _patch_session(monkeypatch, session) -> None:
    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)


def test_consultar_eleitos_filtra_vereadores_em_exercicio(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Eleito(
                tipo_politico="vereador",
                municipio="Arcos",
                estado="MG",
                nome_completo="Carlos David Borges",
                partido="PL",
                mandato_inicio=2025,
                mandato_fim=2028,
                mandato_status="em exercício",
            ),
            Eleito(
                tipo_politico="vereador",
                municipio="Arcos",
                estado="MG",
                nome_completo="Joao Paulo Ferreira",
                partido="PSD",
                mandato_inicio=2021,
                mandato_fim=2024,
                mandato_status="encerrado",
            ),
            Eleito(
                tipo_politico="prefeito",
                municipio="Arcos",
                estado="MG",
                nome_completo="Wellington Roque",
                partido="PL",
                mandato_inicio=2025,
                mandato_fim=2028,
                mandato_status="em exercício",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = eleitos_tools.consultar_eleitos(
        filtros={"tipo_politico": "vereador", "em_exercicio": True},
        ordenar_por="nome",
        ordem="asc",
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["nome_completo"] == "Carlos David Borges"

    session.close()


def test_consultar_eleitos_filtra_por_ano(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Eleito(
                tipo_politico="prefeito",
                municipio="Arcos",
                estado="MG",
                nome_completo="Prefeito A",
                mandato_inicio=2021,
                mandato_fim=2024,
                mandato_status="encerrado",
            ),
            Eleito(
                tipo_politico="prefeito",
                municipio="Arcos",
                estado="MG",
                nome_completo="Prefeito B",
                mandato_inicio=2025,
                mandato_fim=2028,
                mandato_status="em exercício",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = eleitos_tools.consultar_eleitos(
        filtros={"tipo_politico": "prefeito", "ano": 2025},
        campos=["nome_completo", "mandato_inicio", "mandato_fim"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "nome_completo": "Prefeito B",
            "mandato_inicio": 2025,
            "mandato_fim": 2028,
        }
    ]

    session.close()


def test_consultar_eleitos_interpreta_cargo_politico_como_tipo_em_exercicio(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Eleito(
                tipo_politico="prefeito",
                municipio="Arcos",
                estado="MG",
                nome_completo="Wellington Roque",
                cargo="Prefeito Municipal",
                mandato_inicio=2025,
                mandato_fim=2028,
                mandato_status="em exercício",
            ),
            Eleito(
                tipo_politico="vice-prefeito",
                municipio="Arcos",
                estado="MG",
                nome_completo="Vice Exemplo",
                cargo="Vice-Prefeito",
                mandato_inicio=2025,
                mandato_fim=2028,
                mandato_status="em exercício",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = eleitos_tools.consultar_eleitos(
        filtros={"cargo": "o prefeito", "em_exercicio": True},
        campos=["nome_completo", "tipo_politico"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "nome_completo": "Wellington Roque",
            "tipo_politico": "prefeito",
        }
    ]

    session.close()


def test_consultar_eleitos_retorna_erro_para_tipo_invalido() -> None:
    resultado = eleitos_tools.consultar_eleitos(filtros={"tipo_politico": "deputado"})

    assert resultado["total"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]


def test_consultar_eleitos_retorna_biografia_e_contatos_por_padrao(monkeypatch) -> None:
    session = _build_session()
    session.add(
        Eleito(
            tipo_politico="vereador",
            municipio="Arcos",
            estado="MG",
            nome_completo="Alex Gracieres Ribeiro",
            nome_popular="Alex Didier",
            partido="SD",
            telefone="(37) 3351 3422",
            email="ver.alexribeiro@camaraarcos.mg.gov.br",
            homepage="https://www.arcos.mg.leg.br/",
            biografia="Vereador em primeiro mandato.",
            mandato_inicio=2025,
            mandato_fim=2028,
            mandato_status="em exercício",
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = eleitos_tools.consultar_eleitos(
        filtros={"nome": "alex gracieres"},
        limite=1,
    )

    assert resultado["total"] == 1
    item = resultado["resultados"][0]
    assert item["telefone"] == "(37) 3351 3422"
    assert item["email"] == "ver.alexribeiro@camaraarcos.mg.gov.br"
    assert item["homepage"] == "https://www.arcos.mg.leg.br/"
    assert item["biografia"] == "Vereador em primeiro mandato."

    session.close()
