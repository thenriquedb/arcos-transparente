from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import agents.tools.sql_tools.despesas_por_funcao as despesas_por_funcao_tools
from agents.tools import registry as tools_registry
from agents.router import route_user_query, select_public_tools_for_query
from database import session as session_manager
from database.models import Base, DespesaPorFuncao


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


def test_consultar_despesas_por_funcao_lista_por_funcao(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
                linha_origem=10,
                origem="prefeitura",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="PREFEITURA MUNICIPAL",
                funcao="Saude",
                dotacao_inicial=Decimal("1000000.00"),
                creditos_adicionais=Decimal("250000.00"),
                dotacao_atualizada=Decimal("1250000.00"),
                valor_empenhado=Decimal("800000.00"),
                valor_em_liquidacao=Decimal("600000.00"),
                valor_liquidado=Decimal("580000.00"),
                valor_pago=Decimal("550000.00"),
            ),
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
                linha_origem=11,
                origem="prefeitura",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="PREFEITURA MUNICIPAL",
                funcao="Educacao",
                dotacao_inicial=Decimal("900000.00"),
                creditos_adicionais=Decimal("100000.00"),
                dotacao_atualizada=Decimal("1000000.00"),
                valor_empenhado=Decimal("700000.00"),
                valor_em_liquidacao=Decimal("500000.00"),
                valor_liquidado=Decimal("490000.00"),
                valor_pago=Decimal("470000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = despesas_por_funcao_tools.consultar_despesas_por_funcao(
        filtros={"ano": 2025, "funcao": "saude"},
        campos=["funcao", "valor_pago", "dotacao_atualizada", "periodo_fim"],
    )

    assert resultado["total"] == 1
    assert resultado["resultados"] == [
        {
            "funcao": "Saude",
            "dotacao_atualizada": 1250000.0,
            "valor_pago": 550000.0,
            "periodo_fim": "2025-01-31",
        }
    ]
    assert resultado["metadata"]["campos"] == [
        "funcao",
        "valor_pago",
        "dotacao_atualizada",
        "periodo_fim",
    ]
    assert resultado["metadata"]["explicacao_campos"] == {
        "funcao": "Funcao de governo padronizada nacionalmente, como saude ou educacao.",
        "valor_pago": "Valor efetivamente pago no periodo.",
        "dotacao_atualizada": "Dotacao inicial somada aos creditos adicionais.",
        "periodo_fim": "Data final do periodo consolidado no relatorio.",
    }
    assert resultado["metadata"]["campos_financeiros_prioritarios"] == [
        "valor_empenhado",
        "valor_em_liquidacao",
        "valor_liquidado",
        "valor_pago",
    ]
    assert resultado["metadata"]["explicacao_estagios_despesa"] == {
        "valor_empenhado": "Valor ja comprometido oficialmente pela administracao.",
        "valor_em_liquidacao": "Valor que esta em fase de conferencia antes da liquidacao.",
        "valor_liquidado": "Valor com entrega ou servico reconhecido pela administracao.",
        "valor_pago": "Valor efetivamente pago no periodo.",
    }
    assert (
        resultado["metadata"]["orientacao_gasto_amplo"]
        == "Em perguntas amplas sobre gasto por funcao, nao resuma a resposta em apenas um total. Mostre e diferencie valor_empenhado, valor_em_liquidacao, valor_liquidado e valor_pago."
    )

    session.close()


def test_consultar_despesas_por_funcao_retorna_estagios_financeiros_por_padrao(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        DespesaPorFuncao(
            arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
            linha_origem=10,
            origem="prefeitura",
            exercicio=2025,
            periodo_inicio=date(2025, 1, 1),
            periodo_fim=date(2025, 12, 31),
            unidade_gestora="PREFEITURA MUNICIPAL",
            funcao="Saude",
            dotacao_inicial=Decimal("1000000.00"),
            creditos_adicionais=Decimal("250000.00"),
            dotacao_atualizada=Decimal("1250000.00"),
            valor_empenhado=Decimal("800000.00"),
            valor_em_liquidacao=Decimal("600000.00"),
            valor_liquidado=Decimal("580000.00"),
            valor_pago=Decimal("550000.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = despesas_por_funcao_tools.consultar_despesas_por_funcao(
        filtros={"ano": 2025, "funcao": "saude"},
    )

    assert resultado["total"] == 1
    assert resultado["resultados"][0]["valor_empenhado"] == 800000.0
    assert resultado["resultados"][0]["valor_em_liquidacao"] == 600000.0
    assert resultado["resultados"][0]["valor_liquidado"] == 580000.0
    assert resultado["resultados"][0]["valor_pago"] == 550000.0

    session.close()


def test_consultar_despesas_por_funcao_detecta_funcao_sem_confundir_com_origem(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
                linha_origem=10,
                origem="prefeitura",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="PREFEITURA MUNICIPAL",
                funcao="Saude",
                valor_pago=Decimal("550000.00"),
            ),
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-saude-2025.csv",
                linha_origem=11,
                origem="saude",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="FUMUSA",
                funcao="Administracao",
                valor_pago=Decimal("120000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    decision = route_user_query("Quanto a prefeitura gastou na saude em 2025?")
    tool = select_public_tools_for_query(
        "Quanto a prefeitura gastou na saude em 2025?"
    )[0]
    resultado = tool.invoke(decision.tool_kwargs)

    assert decision.tool_name == "agregar_despesas_por_funcao"
    assert decision.tool_kwargs["filtros"] == {
        "ano": 2025,
        "origem": "prefeitura",
        "funcao": "saude",
    }
    assert getattr(tool, "name", "") == "agregar_despesas_por_funcao"
    assert resultado["valor_total"] == 550000.0

    session.close()


def test_agregar_despesas_por_funcao_por_funcao(monkeypatch) -> None:
    session = _build_session()
    session.add_all(
        [
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
                linha_origem=10,
                origem="prefeitura",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="PREFEITURA MUNICIPAL",
                funcao="Saude",
                valor_pago=Decimal("550000.00"),
            ),
            DespesaPorFuncao(
                arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
                linha_origem=11,
                origem="prefeitura",
                exercicio=2025,
                periodo_inicio=date(2025, 1, 1),
                periodo_fim=date(2025, 1, 31),
                unidade_gestora="PREFEITURA MUNICIPAL",
                funcao="Educacao",
                valor_pago=Decimal("470000.00"),
            ),
        ]
    )
    session.commit()
    _patch_session(monkeypatch, session)

    resultado = despesas_por_funcao_tools.agregar_despesas_por_funcao(
        filtros={"ano": 2025},
        agrupar_por="funcao",
        metrica="soma_valor_pago",
    )

    assert resultado["total_grupos"] == 2
    assert resultado["resultados"][0] == {
        "funcao": "Saude",
        "soma_valor_pago": 550000.0,
    }

    session.close()


def test_registry_expoe_tools_publicas_de_despesas_por_funcao() -> None:
    tool_names = {
        getattr(tool_obj, "name", "")
        for tool_obj in tools_registry.get_public_tools(
            tags=["domain:despesas_por_funcao"]
        )
    }

    assert "consultar_despesas_por_funcao" in tool_names
    assert "agregar_despesas_por_funcao" in tool_names


def test_query_de_despesas_por_funcao_rota_para_tool_publica_dedicada(
    monkeypatch,
) -> None:
    session = _build_session()
    session.add(
        DespesaPorFuncao(
            arquivo_origem="despesas-por-funcao-prefeitura-2025.csv",
            linha_origem=10,
            origem="prefeitura",
            exercicio=2025,
            periodo_inicio=date(2025, 1, 1),
            periodo_fim=date(2025, 1, 31),
            unidade_gestora="PREFEITURA MUNICIPAL",
            funcao="Saude",
            valor_pago=Decimal("550000.00"),
        )
    )
    session.commit()
    _patch_session(monkeypatch, session)

    pergunta = "Qual foi o total pago no relatorio de despesas por funcao em 2025?"
    route = route_user_query(pergunta)
    tool = select_public_tools_for_query(pergunta)[0]
    resultado = tool.invoke(route.tool_kwargs)

    assert route.tool_name == "agregar_despesas_por_funcao"
    assert route.tool_kwargs["agrupar_por"] is None
    assert getattr(tool, "name", "") == "agregar_despesas_por_funcao"
    assert resultado["valor_total"] == 550000.0

    session.close()
