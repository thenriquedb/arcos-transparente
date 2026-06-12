"""Extração do nome da pessoa em perguntas de salário / histórico de folha."""

from __future__ import annotations

import re


REFERENTIAL_NAME_TOKENS = {
    "dele",
    "dela",
    "ele",
    "ela",
    "prefeito",
    "prefeita",
}

# Substantivos de domínio que NUNCA são nome de servidor. Quando o objeto
# extraído para histórico de folha começa com um destes, a pergunta é sobre
# um domínio público (contratos, licitações, despesas…), não sobre salário.
_HISTORICO_NAO_NOME_INICIAIS = frozenset(
    {
        "contrato",
        "contratos",
        "licitacao",
        "licitacoes",
        "pregao",
        "pregoes",
        "edital",
        "editais",
        "despesa",
        "despesas",
        "diaria",
        "diarias",
        "passagem",
        "passagens",
        "repasse",
        "repasses",
        "transferencia",
        "transferencias",
        "emenda",
        "emendas",
        "evento",
        "eventos",
        "show",
        "shows",
        "festival",
        "festivais",
        "gasto",
        "gastos",
        "servico",
        "servicos",
    }
)


def _extract_nome_para_historico(normalized_text: str) -> str | None:
    """Extrai nomes em perguntas sobre salário ou histórico de pagamentos."""

    # Verbos genéricos de busca (pesquise/busque/procure) NÃO geram nome de
    # histórico de folha: só pistas reais de salário/pagamento qualificam.
    patterns = [
        r"salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"salario\s+([a-z\s]+?)(?:\?|$)",
        r"quanto\s+([a-z\s]+?)\s+(?:recebe|recebeu|ganha|ganhou)(?:\?|$)",
        r"quanto\s+(?:recebe|recebeu|ganha|ganhou)\s+([a-z\s]+?)(?:\?|$)",
        r"(?:quanto\s+e\s+)?(?:o\s+)?salario\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
        r"pagamentos\s+(?:do|da|de)\s+([a-z\s]+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized_text)
        if match is None:
            continue
        nome = re.sub(
            r"^(?:servidor publico|servidora publica|servidor|servidora|funcionario|funcionaria)\s+",
            "",
            match.group(1).strip(),
        )
        nome = re.sub(r"^(?:do|da|de|o|a)\s+", "", nome)
        nome_tokens = nome.split()
        if set(nome_tokens).issubset(REFERENTIAL_NAME_TOKENS):
            continue
        # Objeto que começa com substantivo de domínio não é nome de pessoa.
        if nome_tokens and nome_tokens[0] in _HISTORICO_NAO_NOME_INICIAIS:
            continue
        if nome:
            return nome
    return None
