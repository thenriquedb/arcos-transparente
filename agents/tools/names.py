"""Fonte única dos nomes de tools públicas.

Cada tool pública declara o seu nome via `@register(name=...)`; este enum espelha
esses nomes num lugar tipado e centralizado, consumido pela camada de seleção
(`agents/nlu/intents.py`, `agents/chatbot/hybrid_selection.py`) e pelos testes.

O teste `tests/tools/test_tool_names.py` garante que este enum e o registry de
tools nunca divirjam — assim a seleção nunca aponta para uma tool inexistente ou
com nome desatualizado. Ao adicionar/renomear uma tool pública, atualize aqui.
"""

from __future__ import annotations

from enum import StrEnum


class ToolName(StrEnum):
    """Nome canônico de cada tool pública (membro é uma `str` real)."""

    # Servidores e folha (Prefeitura)
    CONSULTAR_SERVIDORES = "consultar_servidores"
    AGREGAR_SERVIDORES = "agregar_servidores"
    BUSCAR_HISTORICO_DE_PAGAMENTOS_DO_SERVIDOR = "buscar_historico_de_pagamentos_do_servidor"

    # Servidores da Camara Municipal
    CONSULTAR_SERVIDORES_CAMARA = "consultar_servidores_camara"
    AGREGAR_SERVIDORES_CAMARA = "agregar_servidores_camara"

    # Contratos
    CONSULTAR_CONTRATOS = "consultar_contratos"
    AGREGAR_CONTRATOS = "agregar_contratos"

    # Licitações
    CONSULTAR_LICITACOES = "consultar_licitacoes"
    AGREGAR_LICITACOES = "agregar_licitacoes"

    # Planejamento
    CONSULTAR_PLANEJAMENTO = "consultar_planejamento"
    AGREGAR_PLANEJAMENTO = "agregar_planejamento"

    # Receitas
    CONSULTAR_RECEITAS = "consultar_receitas"
    AGREGAR_RECEITAS = "agregar_receitas"

    # Despesas
    CONSULTAR_DESPESAS = "consultar_despesas"
    AGREGAR_DESPESAS = "agregar_despesas"

    # Despesas por função
    CONSULTAR_DESPESAS_POR_FUNCAO = "consultar_despesas_por_funcao"
    AGREGAR_DESPESAS_POR_FUNCAO = "agregar_despesas_por_funcao"

    # Diárias
    CONSULTAR_DIARIAS = "consultar_diarias"
    AGREGAR_DIARIAS = "agregar_diarias"

    # Passagens
    CONSULTAR_PASSAGENS = "consultar_passagens"
    AGREGAR_PASSAGENS = "agregar_passagens"

    # Transferências financeiras / emendas
    CONSULTAR_TRANSFERENCIAS_FINANCEIRAS = "consultar_transferencias_financeiras"
    AGREGAR_TRANSFERENCIAS_FINANCEIRAS = "agregar_transferencias_financeiras"

    # Estoques
    CONSULTAR_ESTOQUES = "consultar_estoques"
    AGREGAR_ESTOQUES = "agregar_estoques"
    CONSULTAR_MOVIMENTACOES_DE_ESTOQUE = "consultar_movimentacoes_de_estoque"

    # Patrimônios
    CONSULTAR_PATRIMONIOS = "consultar_patrimonios"
    AGREGAR_PATRIMONIOS = "agregar_patrimonios"

    # Quadro de pessoal
    CONSULTAR_QUADRO_PESSOAL = "consultar_quadro_pessoal"
    AGREGAR_QUADRO_PESSOAL = "agregar_quadro_pessoal"

    # Frota
    CONSULTAR_FROTA = "consultar_frota"
    AGREGAR_FROTA = "agregar_frota"

    # Folha de pagamento por cargo e lotação
    CONSULTAR_FOLHA_CARGOS = "consultar_folha_cargos"
    AGREGAR_FOLHA_CARGOS = "agregar_folha_cargos"
    CONSULTAR_FOLHA_LOTACOES = "consultar_folha_lotacoes"
    AGREGAR_FOLHA_LOTACOES = "agregar_folha_lotacoes"

    # Histórico funcional de servidor
    CONSULTAR_HISTORICO_FUNCIONAL_SERVIDOR = "consultar_historico_funcional_servidor"

    # Itens adquiridos em contratos
    CONSULTAR_ITENS_ADQUIRIDOS_CONTRATO = "consultar_itens_adquiridos_contrato"

    # Despesas por veículo de frota
    CONSULTAR_DESPESAS_FROTA = "consultar_despesas_frota"
    AGREGAR_DESPESAS_FROTA = "agregar_despesas_frota"

    # Eleitos
    CONSULTAR_ELEITOS = "consultar_eleitos"

    # Conhecimento municipal (RAG)
    CONSULTAR_CONHECIMENTO_MUNICIPAL = "consultar_conhecimento_municipal"
