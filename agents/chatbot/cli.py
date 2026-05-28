"""CLI simples para testar o chatbot do agente.

Uso:
    python -m agents.chatbot.cli
    python -m agents.chatbot.cli --once "Liste os contratos de 2025"
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from agents.chatbot.core import ChatSession, ChatbotApplication

EXIT_COMMANDS = {"sair", "exit", "quit", ":q"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m agents.chatbot.cli",
        description="Chat CLI simples para testar o agente Arcos Transparente.",
    )
    parser.add_argument(
        "--session-id",
        default="chatbot-cli",
        help="Identificador da sessao de memoria do agente.",
    )
    parser.add_argument(
        "--once",
        metavar="PERGUNTA",
        help="Executa uma unica pergunta e encerra.",
    )
    return parser


def run_once(
    app: ChatbotApplication,
    question: str,
    output: Callable[[str], None] = print,
) -> int:
    response = app.ask(question)
    output(response.content)
    return 0


def run_interactive(
    app: ChatbotApplication,
    input_func: Callable[[str], str] = input,
    output: Callable[[str], None] = print,
) -> int:
    output("=== Chat Arcos Transparente ===")
    output("Digite 'sair' para encerrar.")

    while True:
        try:
            question = input_func("Voce: ").strip()
        except EOFError:
            output("")
            return 0

        if not question:
            continue

        if question.lower() in EXIT_COMMANDS:
            output("Encerrando chat.")
            return 0

        try:
            response = app.ask(question)
        except Exception as exc:
            output(f"[Erro] {exc}")
            continue

        output(f"Agente: {response.content}")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = ChatbotApplication(session=ChatSession(id=args.session_id))

    if args.once:
        return run_once(app, args.once)

    return run_interactive(app)


if __name__ == "__main__":
    raise SystemExit(main())
