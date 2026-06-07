"""Mensagens públicas reutilizadas pelo chatbot."""

from __future__ import annotations


def build_scope_help_message() -> str:
    """Explica de forma objetiva o que o chatbot consegue responder."""

    return (
        "Posso ajudar apenas com consultas aos dados públicos municipais "
        "disponíveis neste sistema e com o acervo municipal curado local.\n\n"
        "**IMPORTANTE: A base local cobre, em geral, de 2025 ate maio de 2026**.\n\n"
        "Voce pode perguntar, por exemplo:\n\n"
        "- **Servidores e secretarias**: `Quem é o secretario de saude?`\n"
        "- **Salarios-base e historico de pagamentos**: `Quanto João Silva recebe?`\n"
        "- **Licitacoes e contratos**: `Quais licitacoes da prefeitura aconteceram em 2025?`\n"
        "- **Despesas, diarias e passagens**: `Quanto a prefeitura gastou com diarias em 2025?`\n"
        "- **Frota, veiculos e patrimonio**: `Quais veiculos fazem parte da frota municipal?`\n"
        "- **Quadro de pessoal, planejamento e receitas**: `Quanto a prefeitura arrecadou em 2025?`\n"
        "- **Transferencias, emendas e politicos eleitos**: `Quanto a prefeitura recebeu de emendas parlamentares em 2025?`\n"
        "- **Telefones uteis, estrutura organizacional e horarios de onibus**: `Qual e o telefone do Procon?`"
    )
