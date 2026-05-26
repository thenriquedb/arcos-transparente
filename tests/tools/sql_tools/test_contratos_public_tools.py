from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.contratos as contratos_tools
from database import session as session_manager
from database.models import Base, Contrato


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


def _build_legacy_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE contratos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                criado_em DATETIME,
                atualizado_em DATETIME,
                numero VARCHAR(50) NOT NULL,
                fornecedor VARCHAR(255) NOT NULL,
                cnpj VARCHAR(18) NOT NULL,
                fornecedor_id INTEGER,
                valor NUMERIC(15, 2) NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE,
                categoria VARCHAR(100) NOT NULL,
                secretaria VARCHAR(120) NOT NULL,
                descricao TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO contratos (
                numero,
                fornecedor,
                cnpj,
                fornecedor_id,
                valor,
                data_inicio,
                data_fim,
                categoria,
                secretaria,
                descricao
            ) VALUES (
                '001/2025',
                'Fornecedor Alfa',
                '123',
                NULL,
                10500,
                '2025-01-10',
                NULL,
                'Servico',
                'Secretaria de Saude',
                'Locacao de estrutura'
            )
            """
        )

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


def _contrato(
    *,
    numero: str,
    fornecedor: str,
    cnpj: str,
    valor: float,
    data_inicio: date,
    data_fim: date | None,
    categoria: str,
    secretaria: str,
    descricao: str,
    descricao_despesa: str | None = None,
) -> Contrato:
    return Contrato(
        numero=numero,
        fornecedor=fornecedor,
        cnpj=cnpj,
        valor=valor,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
        secretaria=secretaria,
        descricao=descricao,
        descricao_despesa=descricao_despesa,
    )


def test_consultar_contratos_filtra_por_secretaria_e_ordena_por_data(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2025",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=10500,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero="002/2025",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=2500,
                data_inicio=date(2025, 2, 5),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Material escolar",
            ),
            _contrato(
                numero="003/2025",
                fornecedor="Fornecedor Gama",
                cnpj="789",
                valor=32000,
                data_inicio=date(2025, 3, 1),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Gestao de evento",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"secretaria": "saude"},
        ordenar_por="data_inicio",
        ordem="desc",
        campos=["numero", "secretaria", "data_inicio"],
    )

    assert resultado["total"] == 2
    assert resultado["resultados"] == [
        {
            "numero": "003/2025",
            "secretaria": "Secretaria de Saude",
            "data_inicio": "2025-03-01",
        },
        {
            "numero": "001/2025",
            "secretaria": "Secretaria de Saude",
            "data_inicio": "2025-01-10",
        },
    ]

    session.close()


def test_consultar_contratos_suporta_ranking_por_valor(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2025",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=10500,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero="002/2025",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=2500,
                data_inicio=date(2025, 2, 5),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Material escolar",
            ),
            _contrato(
                numero="003/2025",
                fornecedor="Fornecedor Gama",
                cnpj="789",
                valor=32000,
                data_inicio=date(2025, 3, 1),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Obras",
                descricao="Obra de infraestrutura",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        ordenar_por="valor",
        ordem="desc",
        limite=2,
        campos=["numero", "valor", "secretaria"],
    )

    assert resultado["total"] == 3
    assert resultado["mensagem"] == "Mostrando 2 de 3 registros encontrados."
    assert resultado["resultados"] == [
        {
            "numero": "003/2025",
            "valor": 32000.0,
            "secretaria": "Secretaria de Obras",
        },
        {
            "numero": "001/2025",
            "valor": 10500.0,
            "secretaria": "Secretaria de Saude",
        },
    ]

    session.close()


def test_consultar_contratos_faz_fallback_de_fornecedor_para_descricao(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="063/2025",
                fornecedor="Walber Henrique Pedroso",
                cnpj="57149336000138",
                valor=0,
                data_inicio=date(2025, 4, 29),
                data_fim=date(2025, 5, 28),
                categoria="Servico",
                secretaria="Prefeitura Municipal",
                descricao="Contratacao de show artistico da banda Sigma 6",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"fornecedor": "Sigma 6"},
        ordenar_por="data_inicio",
        ordem="desc",
        campos=["numero", "fornecedor", "descricao"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "063/2025",
            "fornecedor": "Walber Henrique Pedroso",
            "descricao": "Contratacao de show artistico da banda Sigma 6",
        }
    ]
    assert "descricao" in resultado["mensagem"]
    assert resultado["metadata"]["filtros_aplicados"] == {"fornecedor": "Sigma 6"}
    assert resultado["metadata"]["filtros_fallback_aplicados"] == {
        "descricao": "Sigma 6"
    }

    session.close()


def test_consultar_contratos_busca_em_classificacao_da_despesa(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="178/2025",
                fornecedor="Luiz Fernando Carvalho Bravo",
                cnpj="23974941000121",
                valor=143.0,
                data_inicio=date(2025, 10, 15),
                data_fim=date(2025, 12, 31),
                categoria="Servico",
                secretaria="Prefeitura Municipal",
                descricao="Realizacao do Encontro Municipal dos Grupos de Convivencia de Idosos",
                descricao_despesa="Festividades e Homenagens",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"descricao": "Festividades e Homenagens"},
        campos=["numero", "fornecedor", "classificacao_da_despesa"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "178/2025",
            "fornecedor": "Luiz Fernando Carvalho Bravo",
            "classificacao_da_despesa": "Festividades e Homenagens",
        }
    ]

    session.close()


def test_consultar_contratos_nao_quebra_em_base_antiga_sem_descricao_despesa(
    monkeypatch,
) -> None:
    session = _build_legacy_session()
    _patch_session(monkeypatch, session)

    resultado_por_fornecedor = contratos_tools.consultar_contratos(
        filtros={"fornecedor": "Fornecedor Alfa"},
        campos=["numero", "fornecedor"],
    )
    resultado_por_classificacao = contratos_tools.consultar_contratos(
        filtros={"descricao": "Festividades e Homenagens"},
    )

    assert resultado_por_fornecedor["total"] == 1
    assert resultado_por_fornecedor["resultados"] == [
        {"numero": "001/2025", "fornecedor": "Fornecedor Alfa"}
    ]
    assert resultado_por_classificacao["total"] == 0
    assert (
        "classificacao da despesa"
        in resultado_por_classificacao["sugestao"].lower()
    )

    session.close()


def test_agregar_contratos_soma_total_por_periodo(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2025",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=10000,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero="002/2025",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=5000,
                data_inicio=date(2025, 4, 5),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Material escolar",
            ),
            _contrato(
                numero="003/2025",
                fornecedor="Fornecedor Gama",
                cnpj="789",
                valor=3000,
                data_inicio=date(2024, 12, 20),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Item anterior",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.agregar_contratos(
        filtros={
            "data_inicio_inicio": "2025-01-01",
            "data_inicio_fim": "2025-12-31",
        },
        metrica="soma_valor",
    )

    assert resultado["total_grupos"] == 0
    assert resultado["valor_total"] == 15000.0

    session.close()


def test_agregar_contratos_ranking_por_secretaria(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2025",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=10000,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero="002/2025",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=5000,
                data_inicio=date(2025, 4, 5),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Material escolar",
            ),
            _contrato(
                numero="003/2025",
                fornecedor="Fornecedor Gama",
                cnpj="789",
                valor=9000,
                data_inicio=date(2025, 6, 8),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Uniformes",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.agregar_contratos(
        agrupar_por="secretaria",
        metrica="contagem",
        ordenar_por="metrica",
        ordem="desc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"secretaria": "Secretaria de Educacao", "contagem": 2},
        {"secretaria": "Secretaria de Saude", "contagem": 1},
    ]

    session.close()
