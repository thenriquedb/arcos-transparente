from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.contratos as contratos_tools
from database import session as session_manager
from database.session import _normalizar_texto
from database.models import (
    Base,
    Contrato,
    ContratoDespesaOrcamentaria,
    ContratoItemAdquirido,
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


def _build_legacy_session():
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def on_connect(conn, _):
        conn.create_function("normalizar", 1, _normalizar_texto)

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
    numero_licitatorio: str | None = None,
    numero_instrumento: str | None = None,
    tipo_instrumento_contratual: str | None = None,
    possui_aditivo: str | None = None,
    xml_original: str | None = None,
) -> Contrato:
    return Contrato(
        numero=numero,
        numero_licitatorio=numero_licitatorio,
        numero_instrumento=numero_instrumento,
        tipo_instrumento_contratual=tipo_instrumento_contratual,
        fornecedor=fornecedor,
        cnpj=cnpj,
        valor=valor,
        data_inicio=data_inicio,
        data_fim=data_fim,
        categoria=categoria,
        secretaria=secretaria,
        possui_aditivo=possui_aditivo,
        descricao=descricao,
        descricao_despesa=descricao_despesa,
        xml_original=xml_original,
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


def test_consultar_contratos_filtra_por_vigencia_na_data(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2024",
                fornecedor="Fornecedor Plurianual",
                cnpj="123",
                valor=50000,
                data_inicio=date(2024, 5, 1),
                data_fim=date(2027, 4, 30),
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Contrato plurianual em vigencia",
            ),
            _contrato(
                numero="002/2026",
                fornecedor="Fornecedor Encerrado",
                cnpj="456",
                valor=8000,
                data_inicio=date(2026, 1, 10),
                data_fim=date(2026, 3, 31),
                categoria="Servico",
                secretaria="Secretaria de Educacao",
                descricao="Contrato ja encerrado",
            ),
            _contrato(
                numero="003/2025",
                fornecedor="Fornecedor Aberto",
                cnpj="789",
                valor=12000,
                data_inicio=date(2025, 2, 1),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Obras",
                descricao="Contrato com fim em aberto",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"vigente_em": "2026-06-09"},
        ordenar_por="numero",
        ordem="asc",
        campos=["numero"],
    )

    # Plurianual (2024-2027) e fim em aberto contam; o encerrado em mar/2026 nao.
    assert [item["numero"] for item in resultado["resultados"]] == [
        "001/2024",
        "003/2025",
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


def test_consultar_contratos_suporta_ranking_por_valor_filtrado_por_ano(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2024",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=90000,
                data_inicio=date(2024, 12, 30),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Contrato anterior",
            ),
            _contrato(
                numero="001/2025",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=10500,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero="002/2025",
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
        filtros={
            "data_inicio_inicio": "2025-01-01",
            "data_inicio_fim": "2025-12-31",
        },
        ordenar_por="valor",
        ordem="desc",
        limite=10,
        campos=["numero", "valor", "data_inicio"],
    )

    assert resultado["total"] == 2
    assert resultado["resultados"] == [
        {
            "numero": "002/2025",
            "valor": 32000.0,
            "data_inicio": "2025-03-01",
        },
        {
            "numero": "001/2025",
            "valor": 10500.0,
            "data_inicio": "2025-01-10",
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
    assert resultado["metadata"]["filtros_fallback_aplicados"] == {"descricao": "Sigma 6"}

    session.close()


def test_consultar_contratos_faz_fallback_de_fornecedor_para_categoria(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="070/2025",
                fornecedor="Empresa Exemplo Ltda",
                cnpj="11222333000144",
                valor=8000,
                data_inicio=date(2025, 5, 3),
                data_fim=None,
                categoria="Festas e Eventos",
                secretaria="Prefeitura Municipal",
                descricao="Apoio logistico",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"fornecedor": "Festas e Eventos"},
        campos=["numero", "categoria", "fornecedor"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "070/2025",
            "categoria": "Festas e Eventos",
            "fornecedor": "Empresa Exemplo Ltda",
        }
    ]
    assert "categoria" in resultado["mensagem"]
    assert resultado["metadata"]["filtros_fallback_aplicados"] == {"categoria": "Festas e Eventos"}

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


def test_consultar_contratos_busca_numero_em_colunas_alternativas(monkeypatch) -> None:
    session = _build_session()
    session.add(
        _contrato(
            numero="178/2025",
            numero_licitatorio="394/2025",
            numero_instrumento="178/2025",
            fornecedor="Fornecedor Numero Alternativo",
            cnpj="23974941000121",
            valor=143.0,
            data_inicio=date(2025, 10, 15),
            data_fim=date(2025, 12, 31),
            categoria="Servico",
            secretaria="Prefeitura Municipal",
            descricao="Contrato de exemplo",
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"numero": "394/2025"},
        campos=["numero", "fornecedor"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "178/2025",
            "fornecedor": "Fornecedor Numero Alternativo",
        }
    ]

    session.close()


def test_consultar_contratos_busca_no_xml_original_como_ultimo_fallback(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        _contrato(
            numero="090/2025",
            fornecedor="Fornecedor XML",
            cnpj="12345678000199",
            valor=1000,
            data_inicio=date(2025, 7, 1),
            data_fim=None,
            categoria="Servico",
            secretaria="Prefeitura Municipal",
            descricao="Servico comum",
            xml_original=(
                "<InstrumentoContratual><ObservacaoInterna>Projeto Aurora</ObservacaoInterna></InstrumentoContratual>"
            ),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"descricao": "Projeto Aurora"},
        campos=["numero", "fornecedor"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "090/2025",
            "fornecedor": "Fornecedor XML",
        }
    ]

    session.close()


def test_consultar_contratos_nao_confunde_sigla_curta_com_pedaco_de_palavra(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="115/2025",
                fornecedor="Fornecedor Roupa",
                cnpj="12345678000199",
                valor=1000,
                data_inicio=date(2025, 8, 18),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Confeccao de fantasias",
                xml_original="<Identificacao>Roupa professoras</Identificacao>",
            ),
            _contrato(
                numero="172/2025",
                fornecedor="Fornecedor Lupa",
                cnpj="12345678000199",
                valor=1000,
                data_inicio=date(2025, 10, 8),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Aquisicao de materiais pedagogicos",
                xml_original="<Identificacao>Lupa escolar</Identificacao>",
            ),
            _contrato(
                numero="200/2025",
                fornecedor="Fornecedor Saude",
                cnpj="12345678000199",
                valor=1000,
                data_inicio=date(2025, 10, 20),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Manutencao da UPA Municipal",
                xml_original="<Identificacao>UPA Municipal</Identificacao>",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"descricao": "UPA"},
        campos=["numero", "descricao"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "numero": "200/2025",
            "descricao": "Manutencao da UPA Municipal",
        }
    ]

    session.close()


def test_consultar_contratos_inclui_detalhes_quando_solicitado(monkeypatch) -> None:
    session = _build_session()
    contrato = _contrato(
        numero="178/2025",
        numero_licitatorio="394/2025",
        numero_instrumento="178/2025",
        tipo_instrumento_contratual="Contrato",
        fornecedor="Luiz Fernando Carvalho Bravo",
        cnpj="23974941000121",
        valor=143.0,
        data_inicio=date(2025, 10, 15),
        data_fim=date(2025, 12, 31),
        categoria="Servico",
        secretaria="Prefeitura Municipal",
        possui_aditivo="Nao",
        descricao="Realizacao do Encontro Municipal dos Grupos de Convivencia de Idosos",
        descricao_despesa="Festividades e Homenagens",
    )
    contrato.despesas_orcamentarias.append(
        ContratoDespesaOrcamentaria(
            ordem=1,
            unidade_gestora="Prefeitura Municipal",
            exercicio=2025,
            orgao="Prefeitura Municipal",
            unidade="Secretaria Mun. Desenv. e Int. Social",
            fonte_recurso="Recursos nao Vinculados de Impostos",
            natureza_despesa_rubrica="339039200000",
            descricao_despesa="Festividades e Homenagens",
            valor_despesa=69500,
        )
    )
    contrato.itens_adquiridos.append(
        ContratoItemAdquirido(
            ordem=1,
            unidade_gestora="Prefeitura Municipal",
            numero_lote="2",
            numero_item="1",
            identificacao="Servico de decoracao",
            quantidade=1,
            valor_unitario=7724,
            valor_total=7724,
        )
    )
    session.add(contrato)
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.consultar_contratos(
        filtros={"numero": "178/2025"},
        incluir_detalhes=True,
    )

    assert resultado["total"] == 1
    contrato_resultado = resultado["resultados"][0]
    assert contrato_resultado["numero_licitatorio"] == "394/2025"
    assert contrato_resultado["numero_instrumento"] == "178/2025"
    assert contrato_resultado["tipo_do_instrumento"] == "Contrato"
    assert contrato_resultado["possui_aditivo"] == "Nao"
    assert contrato_resultado["total_despesas_orcamentarias"] == 1
    assert contrato_resultado["despesas_orcamentarias"][0]["classificacao_da_despesa"] == ("Festividades e Homenagens")
    assert contrato_resultado["total_itens_adquiridos"] == 1
    assert contrato_resultado["itens_adquiridos"][0]["numero_item"] == "1"

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
    assert resultado_por_fornecedor["resultados"] == [{"numero": "001/2025", "fornecedor": "Fornecedor Alfa"}]
    assert resultado_por_classificacao["total"] == 0
    assert "classificacao da despesa" in resultado_por_classificacao["sugestao"].lower()

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


def test_agregar_contratos_faz_fallback_textual_para_categoria(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero="001/2025",
                fornecedor="Empresa X",
                cnpj="123",
                valor=10000,
                data_inicio=date(2025, 1, 10),
                data_fim=None,
                categoria="Festas e Eventos",
                secretaria="Secretaria de Cultura",
                descricao="Apoio operacional",
            ),
            _contrato(
                numero="002/2025",
                fornecedor="Empresa Y",
                cnpj="456",
                valor=5000,
                data_inicio=date(2025, 1, 12),
                data_fim=None,
                categoria="Festas e Eventos",
                secretaria="Secretaria de Cultura",
                descricao="Estrutura de palco",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.agregar_contratos(
        filtros={"fornecedor": "Festas e Eventos"},
        metrica="contagem",
    )

    assert resultado["valor_total"] == 2
    assert "categoria" in resultado["mensagem"]
    assert resultado["metadata"]["filtros_fallback_aplicados"] == {"categoria": "Festas e Eventos"}

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


def test_agregar_contratos_ranking_por_fornecedor_no_ano_corrente(monkeypatch) -> None:
    current_year = date.today().year
    session = _build_session()
    session.add_all(
        [
            _contrato(
                numero=f"001/{current_year}",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=10000,
                data_inicio=date(current_year, 1, 10),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Saude",
                descricao="Locacao de estrutura",
            ),
            _contrato(
                numero=f"002/{current_year}",
                fornecedor="Fornecedor Alfa",
                cnpj="123",
                valor=5000,
                data_inicio=date(current_year, 4, 5),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Material escolar",
            ),
            _contrato(
                numero=f"003/{current_year}",
                fornecedor="Fornecedor Beta",
                cnpj="456",
                valor=9000,
                data_inicio=date(current_year, 6, 8),
                data_fim=None,
                categoria="Compra",
                secretaria="Secretaria de Educacao",
                descricao="Uniformes",
            ),
            _contrato(
                numero=f"004/{current_year - 1}",
                fornecedor="Fornecedor Gama",
                cnpj="789",
                valor=7000,
                data_inicio=date(current_year - 1, 12, 20),
                data_fim=None,
                categoria="Servico",
                secretaria="Secretaria de Obras",
                descricao="Contrato anterior",
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.agregar_contratos(
        filtros={
            "data_inicio_inicio": f"{current_year}-01-01",
            "data_inicio_fim": f"{current_year}-12-31",
        },
        agrupar_por="fornecedor",
        metrica="contagem",
        ordenar_por="metrica",
        ordem="desc",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"] == [
        {"fornecedor": "Fornecedor Alfa", "contagem": 2},
        {"fornecedor": "Fornecedor Beta", "contagem": 1},
    ]

    session.close()


def test_agregar_contratos_limite_cinco_preserva_empates_de_ranking(
    monkeypatch,
) -> None:
    current_year = date.today().year
    session = _build_session()
    contratos = []
    for indice in range(1, 7):
        for sequencia in range(1, 3):
            contratos.append(
                _contrato(
                    numero=f"{indice:03d}-{sequencia}/{current_year}",
                    fornecedor=f"Fornecedor {indice}",
                    cnpj=f"{indice:03d}",
                    valor=1000 * indice,
                    data_inicio=date(current_year, sequencia, min(10 + indice, 28)),
                    data_fim=None,
                    categoria="Servico",
                    secretaria="Secretaria de Saude",
                    descricao="Contrato empatado",
                )
            )
    session.add_all(contratos)
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = contratos_tools.agregar_contratos(
        filtros={
            "data_inicio_inicio": f"{current_year}-01-01",
            "data_inicio_fim": f"{current_year}-12-31",
        },
        agrupar_por="fornecedor",
        metrica="contagem",
        ordenar_por="metrica",
        ordem="desc",
        limite=5,
    )

    assert resultado["total_grupos"] == 6
    assert len(resultado["resultados"]) == 5
    assert all(item["contagem"] == 2 for item in resultado["resultados"])
    assert resultado["mensagem"] == "Mostrando 5 de 6 grupos encontrados."

    session.close()
