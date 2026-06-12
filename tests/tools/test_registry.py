from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest

import agents.tools.registry as registry
from agents.chatbot.observability import use_observability_provider
from agents.tools.registry import (
    get_all_tools,
    get_public_tool_catalog,
    get_public_tools,
)


def _tool_name(tool_obj) -> str:
    return getattr(tool_obj, "name", getattr(tool_obj, "__name__", ""))


@dataclass
class _RecordedSpan:
    name: str
    inputs: dict[str, object]
    metadata: dict[str, object]
    outputs: dict[str, object] = field(default_factory=dict)
    error_type: str | None = None


class _RecordedSpanHandle:
    def __init__(self, span: _RecordedSpan) -> None:
        self._span = span

    def set_outputs(self, outputs: Mapping[str, object] | None = None) -> None:
        if outputs:
            self._span.outputs.update(outputs)

    def set_metadata(self, metadata: Mapping[str, object] | None = None) -> None:
        if metadata:
            self._span.metadata.update(metadata)

    def record_error(self, error: BaseException) -> None:
        self._span.error_type = error.__class__.__name__


class _RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.completed_spans: list[_RecordedSpan] = []

    @contextmanager
    def span(
        self,
        name: str,
        *,
        run_type: str = "tool",
        inputs: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
        tags: Sequence[str] | None = None,
    ) -> Iterator[_RecordedSpanHandle]:
        _ = (run_type, tags)
        span = _RecordedSpan(
            name=name,
            inputs=dict(inputs or {}),
            metadata=dict(metadata or {}),
        )
        handle = _RecordedSpanHandle(span)
        try:
            yield handle
        except Exception as exc:
            handle.record_error(exc)
            raise
        finally:
            self.completed_spans.append(span)


def test_get_public_tools_reduz_superficie_para_capabilidades_publicas() -> None:
    public_tool_names = {_tool_name(tool_obj) for tool_obj in get_public_tools()}

    assert public_tool_names == {
        "consultar_servidores",
        "agregar_servidores",
        "consultar_historico_funcional_servidor",
        "consultar_contratos",
        "agregar_contratos",
        "consultar_itens_adquiridos_contrato",
        "consultar_licitacoes",
        "agregar_licitacoes",
        "consultar_receitas",
        "agregar_receitas",
        "consultar_planejamento",
        "agregar_planejamento",
        "consultar_despesas",
        "agregar_despesas",
        "consultar_despesas_por_funcao",
        "agregar_despesas_por_funcao",
        "consultar_diarias",
        "agregar_diarias",
        "consultar_passagens",
        "agregar_passagens",
        "consultar_estoques",
        "agregar_estoques",
        "consultar_movimentacoes_de_estoque",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "consultar_frota",
        "agregar_frota",
        "consultar_despesas_frota",
        "consultar_folha_cargos",
        "agregar_folha_cargos",
        "consultar_folha_lotacoes",
        "agregar_folha_lotacoes",
        "consultar_transferencias_financeiras",
        "agregar_transferencias_financeiras",
        "buscar_historico_de_pagamentos_do_servidor",
        "consultar_conhecimento_municipal",
    }


def test_get_all_tools_converge_para_mesma_superficie_publica() -> None:
    tool_names = {_tool_name(tool_obj) for tool_obj in get_all_tools()}

    assert tool_names == {
        "consultar_servidores",
        "agregar_servidores",
        "consultar_historico_funcional_servidor",
        "consultar_contratos",
        "agregar_contratos",
        "consultar_itens_adquiridos_contrato",
        "consultar_licitacoes",
        "agregar_licitacoes",
        "consultar_receitas",
        "agregar_receitas",
        "consultar_planejamento",
        "agregar_planejamento",
        "consultar_despesas",
        "agregar_despesas",
        "consultar_despesas_por_funcao",
        "agregar_despesas_por_funcao",
        "consultar_diarias",
        "agregar_diarias",
        "consultar_passagens",
        "agregar_passagens",
        "consultar_estoques",
        "agregar_estoques",
        "consultar_movimentacoes_de_estoque",
        "consultar_patrimonios",
        "agregar_patrimonios",
        "consultar_quadro_pessoal",
        "agregar_quadro_pessoal",
        "consultar_eleitos",
        "consultar_frota",
        "agregar_frota",
        "consultar_despesas_frota",
        "consultar_folha_cargos",
        "agregar_folha_cargos",
        "consultar_folha_lotacoes",
        "agregar_folha_lotacoes",
        "consultar_transferencias_financeiras",
        "agregar_transferencias_financeiras",
        "buscar_historico_de_pagamentos_do_servidor",
        "consultar_conhecimento_municipal",
    }


def test_get_all_tools_nao_expoe_nomes_antigos_de_servidores() -> None:
    tool_names = {_tool_name(tool_obj) for tool_obj in get_all_tools()}

    assert "buscar_servidores_por_nome" not in tool_names
    assert "buscar_servidores_por_secretaria" not in tool_names
    assert "listar_servidores_da_secretaria" not in tool_names
    assert "contar_servidores_por_secretaria" not in tool_names
    assert "buscar_servidores_por_cargo" not in tool_names
    assert "listar_maiores_salarios" not in tool_names
    assert "buscar_servidores_por_mes_de_referencia_no_periodo" not in tool_names
    assert "listar_secretarias_por_quantidade_de_servidores" not in tool_names
    assert "buscar_secretaria_com_mais_servidores" not in tool_names


def test_get_all_tools_nao_duplica_tools_em_chamadas_repetidas() -> None:
    primeira_chamada = get_all_tools()
    segunda_chamada = get_all_tools()

    nomes_primeira = [_tool_name(tool_obj) for tool_obj in primeira_chamada]
    nomes_segunda = [_tool_name(tool_obj) for tool_obj in segunda_chamada]

    assert nomes_primeira == nomes_segunda
    assert len(nomes_primeira) == len(set(nomes_primeira))


def test_catalogo_publico_expoe_metadados_de_roteamento_para_todas_as_tools() -> None:
    catalog = get_public_tool_catalog()

    assert len(catalog) == 39
    for entry in catalog:
        assert entry.routing.summary
        assert len(entry.routing.examples) >= 2
        assert len(entry.routing.hints) >= 3


def test_descricoes_orientam_salario_de_cargo_eleito_para_folha() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    consultar_eleitos = tools["consultar_eleitos"].description
    consultar_servidores = tools["consultar_servidores"].description
    buscar_historico = tools["buscar_historico_de_pagamentos_do_servidor"].description

    assert "salario do" in consultar_eleitos
    assert "prefeito" in consultar_eleitos
    assert "buscar_historico_de_pagamentos_do_servidor" in consultar_eleitos
    assert "NAO use para responder salario individual" in consultar_servidores
    assert "use antes `consultar_eleitos`" in consultar_servidores
    assert "primeiro use `consultar_eleitos`" in buscar_historico


def test_descricao_de_conhecimento_municipal_exige_citacao_e_limites() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao = tools["consultar_conhecimento_municipal"].description
    descricao_frota = tools["consultar_frota"].description

    assert "telefones úteis" in descricao
    assert "arquivo_fonte" in descricao
    assert "NAO use esta tool como fonte final para salarios" in descricao
    assert "NAO use para horarios de onibus" in descricao_frota


def test_descricao_de_contratos_orienta_confirmar_siglas_ambiguas() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao = tools["consultar_contratos"].description

    assert "sigla curta ou termo ambiguo" in descricao
    assert "UPA" in descricao
    assert "primeiro confirme o significado" in descricao


def test_descricoes_de_contratos_e_licitacoes_orientam_encadeamento() -> None:
    tools = {_tool_name(tool_obj): tool_obj for tool_obj in get_public_tools()}

    descricao_contratos = tools["consultar_contratos"].description
    descricao_licitacoes = tools["consultar_licitacoes"].description

    assert "R$ 0,00" in descricao_contratos
    assert "consultar_licitacoes" in descricao_contratos
    assert "consultar_despesas" in descricao_contratos
    assert "resultado vazio" in descricao_contratos
    assert "resultado vazio" in descricao_licitacoes
    assert "consultar_contratos" in descricao_licitacoes
    assert "valor estimado R$ 0,00" in descricao_licitacoes


def test_wrapper_publico_emite_observabilidade_com_argumentos_sanitizados() -> None:
    provider = _RecordingProvider()

    def consultar_demo(termo: str, api_key: str) -> dict[str, object]:
        return {
            "termo": termo,
            "api_key": api_key,
        }

    consultar_demo._tool_name = "consultar_demo"

    wrapped = registry._wrap_public_tool_with_observability(consultar_demo)

    with use_observability_provider(provider):
        result = wrapped("alcool", api_key="super-secret")

    assert result["termo"] == "alcool"
    span = provider.completed_spans[-1]

    assert span.name == "chatbot.tool"
    assert span.inputs["tool_name"] == "consultar_demo"
    assert span.inputs["tool_arguments"]["api_key"] == "[REDACTED]"
    assert span.outputs["status"] == "completed"
    assert span.outputs["output_summary"]["kind"] == "mapping"


def test_wrapper_publico_registra_falha_sem_quebrar_contrato() -> None:
    provider = _RecordingProvider()

    def consultar_demo() -> dict[str, object]:
        raise RuntimeError("falha na tool")

    consultar_demo._tool_name = "consultar_demo"

    wrapped = registry._wrap_public_tool_with_observability(consultar_demo)

    with (
        use_observability_provider(provider),
        pytest.raises(
            RuntimeError,
            match="falha na tool",
        ),
    ):
        wrapped()

    span = provider.completed_spans[-1]

    assert span.metadata["status"] == "error"
    assert span.metadata["error_type"] == "RuntimeError"
    assert span.error_type == "RuntimeError"
