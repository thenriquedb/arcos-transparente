"""Helpers de data compartilhados entre subsistemas.

Concentra a fonte unica da data atual e a construcao do bloco de "data atual"
anexado ao system prompt. Manter isso em `shared/` garante que todos os escopos
(contratos, despesas, receitas, folha, planejamento, etc.) resolvam expressoes
relativas — "hoje", "ontem", "mes passado" — contra o mesmo relogio e com as
mesmas regras, sem duplicar logica por dominio.
"""

from __future__ import annotations

from datetime import date


def current_date() -> date:
    """Fonte unica da data atual do runtime.

    Centralizar a leitura do relogio aqui permite que a camada de roteamento e o
    system prompt usem a mesma referencia e que testes a substituam num so ponto.
    """

    return date.today()


def build_current_date_prompt_block(today: date | None = None) -> str:
    """Bloco de system prompt com a data atual e regras de datas relativas.

    O LLM nao conhece a data de execucao; sem ela, nao consegue resolver "hoje",
    "ontem" ou "mes passado" para valores concretos e acaba inventando ou pedindo
    a data ao usuario. Este bloco e anexado ao prompt de todos os escopos, entao
    a orientacao precisa ser agnostica de dominio: cada ferramenta recebe a data
    ja resolvida no formato que seus filtros aceitam.
    """

    hoje = today or current_date()
    return (
        "## Data Atual\n\n"
        f"Hoje é {hoje.strftime('%d/%m/%Y')} (ISO {hoje.isoformat()}). Use esta "
        "data como referência para resolver qualquer expressão de tempo relativa "
        "antes de chamar uma ferramenta, convertendo-a em datas concretas "
        "(`YYYY-MM-DD`) ou em ano/mês conforme os filtros disponíveis:\n\n"
        '- "hoje", "atual", "atualmente", "vigente", "em vigência" → a data de '
        "hoje. Em contratos, isso corresponde ao filtro `vigente_em` com a data "
        "de hoje.\n"
        '- "ontem" → hoje − 1 dia; "anteontem" → hoje − 2 dias; "amanhã" → '
        "hoje + 1 dia.\n"
        '- "esta semana" / "semana passada" → o intervalo de segunda a domingo '
        "correspondente.\n"
        '- "este mês" → do dia 1º até hoje; "mês passado" → do 1º ao último dia '
        "do mês anterior.\n"
        '- "este ano" → o ano atual; "ano passado" → o ano anterior.\n'
        '- "últimos N dias" / "últimos N meses" → o intervalo de N dias/meses '
        "atrás até hoje.\n\n"
        "Quando a data puder ser derivada de hoje, nunca peça o período ao "
        "usuário e nunca invente um ano: calcule a partir da data de hoje."
    )
