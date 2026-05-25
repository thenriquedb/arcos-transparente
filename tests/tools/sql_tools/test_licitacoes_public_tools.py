from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.licitacoes as licitacoes_tools
from database import session as session_manager
from database.models import (
    Base,
    Fornecedor,
    InstrumentoContratual,
    Licitacao,
    MateriaInstrumento,
    VencedorLicitacao,
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


def _patch_session(monkeypatch, session) -> None:
    @contextmanager
    def fake_get_session():
        yield session

    monkeypatch.setattr(session_manager, "get_session", fake_get_session)


def test_consultar_licitacoes_filtra_por_secretaria_e_ordena_por_data(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="001/2025",
                modalidade="Pregao",
                objeto="Compra de medicamentos",
                valor_estimado=100000,
                data_abertura=date(2025, 1, 15),
                situacao="Homologada",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="002/2025",
                modalidade="Pregao",
                objeto="Reforma de escola",
                valor_estimado=250000,
                data_abertura=date(2025, 2, 10),
                situacao="Em andamento",
                secretaria="Secretaria de Educacao",
            ),
            Licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                objeto="Ambulancia",
                valor_estimado=300000,
                data_abertura=date(2025, 3, 1),
                situacao="Aberta",
                secretaria="Secretaria de Saude",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.consultar_licitacoes(
        filtros={"secretaria": "saude"},
        ordenar_por="data_abertura",
        ordem="desc",
        campos=["numero", "secretaria", "data_abertura"],
    )

    assert resultado["total"] == 2
    assert resultado["resultados"] == [
        {
            "numero": "003/2025",
            "secretaria": "Secretaria de Saude",
            "data_abertura": "2025-03-01",
        },
        {
            "numero": "001/2025",
            "secretaria": "Secretaria de Saude",
            "data_abertura": "2025-01-15",
        },
    ]

    session.close()


def test_consultar_licitacoes_suporta_ranking_por_valor(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="001/2025",
                modalidade="Pregao",
                objeto="Compra de medicamentos",
                valor_estimado=100000,
                data_abertura=date(2025, 1, 15),
                situacao="Homologada",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="002/2025",
                modalidade="Pregao",
                objeto="Reforma de escola",
                valor_estimado=250000,
                data_abertura=date(2025, 2, 10),
                situacao="Em andamento",
                secretaria="Secretaria de Educacao",
            ),
            Licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                objeto="Obra viaria",
                valor_estimado=500000,
                data_abertura=date(2025, 3, 1),
                situacao="Aberta",
                secretaria="Secretaria de Obras",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.consultar_licitacoes(
        ordenar_por="valor_estimado",
        ordem="desc",
        limite=2,
        campos=["numero", "valor_estimado", "secretaria"],
    )

    assert resultado["total"] == 3
    assert resultado["mensagem"] == "Mostrando 2 de 3 registros encontrados."
    assert resultado["resultados"] == [
        {
            "numero": "003/2025",
            "valor_estimado": 500000.0,
            "secretaria": "Secretaria de Obras",
        },
        {
            "numero": "002/2025",
            "valor_estimado": 250000.0,
            "secretaria": "Secretaria de Educacao",
        },
    ]

    session.close()


def test_consultar_licitacoes_busca_objeto_sem_acento_e_soma_total(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="118/2025",
                modalidade="Pregao",
                objeto="Contratação de show para o Festival Gastronômico 2025",
                valor_estimado=140000,
                data_abertura=date(2025, 4, 22),
                situacao="Homologada",
                secretaria="Prefeitura Municipal",
            ),
            Licitacao(
                numero="147/2025",
                modalidade="Inexigibilidade",
                objeto="Contratação de show no festival gastronomico",
                valor_estimado=10000,
                data_abertura=date(2025, 4, 29),
                situacao="Concluida",
                secretaria="Prefeitura Municipal",
            ),
            Licitacao(
                numero="026/2025",
                modalidade="Pregao",
                objeto="Decoração para Festival de Gastronomia e outros eventos",
                valor_estimado=326400,
                data_abertura=date(2025, 1, 10),
                situacao="Concluida",
                secretaria="Prefeitura Municipal",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.consultar_licitacoes(
        filtros={
            "objeto": "festival gastronomico",
            "data_abertura_inicio": "2025-01-01",
            "data_abertura_fim": "2025-12-31",
        },
        limite=100,
        campos=["numero", "objeto", "valor_estimado"],
    )

    assert resultado["total"] == 2
    assert resultado["valor_total_estimado"] == 150000.0
    assert resultado["resultados"] == [
        {
            "numero": "147/2025",
            "objeto": "Contratação de show no festival gastronomico",
            "valor_estimado": 10000.0,
        },
        {
            "numero": "118/2025",
            "objeto": "Contratação de show para o Festival Gastronômico 2025",
            "valor_estimado": 140000.0,
        },
    ]

    session.close()


def test_consultar_licitacoes_inclui_detalhes_quando_solicitado(monkeypatch) -> None:
    session = _build_session()
    fornecedor = Fornecedor(cnpj_cpf="12345678000199", nome="Fornecedor Exemplo")
    licitacao = Licitacao(
        numero="004/2025",
        modalidade="Pregao",
        objeto="Compra de merenda escolar",
        valor_estimado=120000,
        data_abertura=date(2025, 4, 20),
        situacao="Homologada",
        secretaria="Secretaria de Educacao",
    )
    licitacao.vencedores.append(
        VencedorLicitacao(
            cnpj_cpf="12345678000199",
            nome="Fornecedor Exemplo",
            validade_proposta="60 dias",
            fornecedor=fornecedor,
        )
    )
    instrumento = InstrumentoContratual(
        fornecedor=fornecedor,
        numero_instrumento="CT-001/2025",
        tipo_instrumento_contratual="Contrato",
        tipo_contrato="Fornecimento",
        objeto="Fornecimento de alimentos",
        data_emissao=date(2025, 5, 1),
        data_expiracao=date(2025, 12, 31),
        possui_aditivo="Nao",
        valor_instrumento_contratual=110000,
    )
    instrumento.materias.append(
        MateriaInstrumento(
            numero_lote="1",
            numero_item="1",
            identificacao="Arroz",
            quantidade=100,
            valor_unitario=5,
            valor_total=500,
        )
    )
    licitacao.instrumentos_contratuais.append(instrumento)
    session.add(licitacao)
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.consultar_licitacoes(
        filtros={"numero": "004/2025"},
        incluir_detalhes=True,
    )

    assert resultado["total"] == 1
    item = resultado["resultados"][0]
    assert item["numero"] == "004/2025"
    assert item["total_vencedores"] == 1
    assert item["vencedores"][0]["nome"] == "Fornecedor Exemplo"
    assert item["total_instrumentos"] == 1
    assert item["instrumentos"][0]["fornecedor"] == "Fornecedor Exemplo"
    assert item["instrumentos"][0]["itens"][0]["identificacao"] == "Arroz"

    session.close()


def test_agregar_licitacoes_conta_sem_agrupar(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="001/2025",
                modalidade="Pregao",
                objeto="Compra de medicamentos",
                valor_estimado=100000,
                data_abertura=date(2025, 1, 15),
                situacao="Homologada",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="002/2025",
                modalidade="Pregao",
                objeto="Ambulancia",
                valor_estimado=300000,
                data_abertura=date(2025, 2, 10),
                situacao="Aberta",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                objeto="Reforma de escola",
                valor_estimado=250000,
                data_abertura=date(2025, 3, 1),
                situacao="Aberta",
                secretaria="Secretaria de Educacao",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.agregar_licitacoes(
        filtros={"secretaria": "saude"},
        metrica="contagem",
    )

    assert resultado["total_grupos"] == 0
    assert resultado["valor_total"] == 2

    session.close()


def test_agregar_licitacoes_ranqueia_secretarias_por_valor(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="001/2025",
                modalidade="Pregao",
                objeto="Compra de medicamentos",
                valor_estimado=100000,
                data_abertura=date(2025, 1, 15),
                situacao="Homologada",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="002/2025",
                modalidade="Pregao",
                objeto="Ambulancia",
                valor_estimado=300000,
                data_abertura=date(2025, 2, 10),
                situacao="Aberta",
                secretaria="Secretaria de Saude",
            ),
            Licitacao(
                numero="003/2025",
                modalidade="Concorrencia",
                objeto="Reforma de escola",
                valor_estimado=250000,
                data_abertura=date(2025, 3, 1),
                situacao="Aberta",
                secretaria="Secretaria de Educacao",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.agregar_licitacoes(
        agrupar_por="secretaria",
        metrica="soma_valor_estimado",
        ordenar_por="metrica",
        ordem="desc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"secretaria": "Secretaria de Saude", "soma_valor_estimado": 400000.0},
        {"secretaria": "Secretaria de Educacao", "soma_valor_estimado": 250000.0},
    ]

    session.close()


def test_agregar_licitacoes_soma_objeto_sem_acento(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            Licitacao(
                numero="118/2025",
                modalidade="Pregao",
                objeto="Contratação de show para o Festival Gastronômico 2025",
                valor_estimado=140000,
                data_abertura=date(2025, 4, 22),
                situacao="Homologada",
                secretaria="Prefeitura Municipal",
            ),
            Licitacao(
                numero="147/2025",
                modalidade="Inexigibilidade",
                objeto="Contratação de show no festival gastronomico",
                valor_estimado=10000,
                data_abertura=date(2025, 4, 29),
                situacao="Concluida",
                secretaria="Prefeitura Municipal",
            ),
            Licitacao(
                numero="026/2025",
                modalidade="Pregao",
                objeto="Decoração para Festival de Gastronomia e outros eventos",
                valor_estimado=326400,
                data_abertura=date(2025, 1, 10),
                situacao="Concluida",
                secretaria="Prefeitura Municipal",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = licitacoes_tools.agregar_licitacoes(
        filtros={"objeto": "festival gastronomico"},
        metrica="soma_valor_estimado",
    )

    assert resultado["total_grupos"] == 0
    assert resultado["valor_total"] == 150000.0

    session.close()


def test_consultar_licitacoes_valida_periodo_invalido() -> None:
    resultado = licitacoes_tools.consultar_licitacoes(
        filtros={
            "data_abertura_inicio": "01/03/2025",
            "data_abertura_fim": "01/02/2025",
        }
    )

    assert resultado["total"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]


def test_agregar_licitacoes_valida_combinacao_invalida() -> None:
    resultado = licitacoes_tools.agregar_licitacoes(
        agrupar_por="secretaria",
        ordenar_por="numero",
    )

    assert resultado["total_grupos"] == 0
    assert "Parametros invalidos" in resultado["mensagem"]
