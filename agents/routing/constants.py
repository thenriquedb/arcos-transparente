"""Constantes de palavras-chave e patterns usadas pelo router."""

from __future__ import annotations


PROMPT_INJECTION_PATTERNS = (
    r"\b(?:ignore|disregard|override|bypass)\b.{0,80}\b(?:instruction|instructions|prompt|system|developer|rules?)\b",
    r"\b(?:desconsidere|ignore|ignore todas|ignore todos|ignore as|ignore os|burle|contorne)\b.{0,80}\b(?:instrucoes|instrução|instrucao|regras?|prompt|sistema|desenvolvedor|developer)\b",
    r"\b(?:revele|mostre|exiba|imprima|print|display)\b.{0,80}\b(?:prompt|system prompt|mensagem de sistema|developer message|mensagem do desenvolvedor)\b",
    r"\b(?:nao use|nao utilize|do not use|never use)\b.{0,30}\b(?:todas as tools|todas as ferramentas|any tools|nenhuma tool)\b",
)

SECRETARIAS_CONHECIDAS = (
    "saude",
    "educacao",
    "obras",
    "financas",
    "administracao",
    "procuradoria",
    "assistencia social",
    "meio ambiente",
    "planejamento",
    "transporte",
)

SUPPORTED_SCOPE_STRONG_KEYWORDS = (
    "prefeitura",
    "municipal",
    "licitacao",
    "licitacoes",
    "pregao",
    "pregoes",
    "edital",
    "editais",
    "fornecedor",
    "fornecedores",
    "vencedor",
    "vencedores",
    "contrato",
    "contratos",
    "contratado",
    "contratada",
    "contratados",
    "contratadas",
    "instrumento",
    "instrumentos",
    "planejamento",
    "planejamentos",
    "orcamento",
    "orcamentario",
    "orcamentaria",
    "dotacao",
    "empenhado",
    "liquidado",
    "servidor",
    "servidores",
    "funcionario",
    "funcionarios",
    "secretaria",
    "secretarias",
    "cargo",
    "cargos",
    "folha",
    "pagamento",
    "pagamentos",
    "fumusa",
)

SUPPORTED_SCOPE_WEAK_KEYWORDS = (
    "salario",
    "salarios",
    "recebeu",
    "recebe",
    "gasto",
    "gastos",
    "pago",
    "pagos",
    "trabalha",
    "trabalham",
    "saude",
    "educacao",
    "obras",
    "procuradoria",
)

LICITACOES_DOMAIN_KEYWORDS = (
    "licitacao",
    "licitacoes",
    "pregao",
    "pregoes",
    "edital",
    "editais",
    "instrumento",
    "instrumentos",
)

CONTRATOS_DOMAIN_KEYWORDS = (
    "contrato",
    "contratos",
    "contratado",
    "contratada",
    "contratados",
    "contratadas",
)

PLANEJAMENTO_DIRECT_KEYWORDS = (
    "planejamento",
    "planejamentos",
    "orcamento",
    "orcamentario",
    "orcamentaria",
    "dotacao",
    "empenhado",
    "liquidado",
)

PLANEJAMENTO_ENTITY_HINT_KEYWORDS = (
    "planejado",
    "planejada",
    "recurso",
    "recursos",
    "verba",
    "verbas",
    "programa",
    "acao",
    "acoes",
    "gasto",
    "gastos",
    "pago",
    "pagos",
)
