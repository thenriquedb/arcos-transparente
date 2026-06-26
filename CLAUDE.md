# Arcos Transparente

Citizen-facing transparency chatbot over ingested municipal public data for the
city of Arcos (MG). A pipeline ingests public XML/CSV files into a normalized
SQLite database; a LangChain agent answers natural-language questions using broad
per-domain SQL tools plus semantic retrieval (RAG) over a curated markdown/PDF
corpus. The default surface is a FastAPI app that serves an institutional landing
page plus a Chainlit chat UI (single process); a CLI chat also exists.

> Read `CONTEXT.md` for the project's domain language and `docs/` for deeper
> architecture notes.

## Stack

Python 3.13+ · `uv` (package manager) · Typer + Rich (CLI) · SQLAlchemy 2 +
Alembic + SQLite · Pydantic 2 · LangChain + LangGraph · OpenAI (`gpt-4.1-mini`
default) · Chroma (RAG vector store) · FastAPI + Jinja2 (landing) + Chainlit (chat
UI) · Loguru · pytest + Ruff · Docker. No static type checker is configured (Ruff only).

## Common commands

```bash
uv sync                                   # install deps
cp .env.example .env                       # then fill OPENAI_API_KEY

uv run python cli.py db init               # create DB + apply migrations
uv run python cli.py db status             # row counts + current migration
uv run python cli.py importar              # import everything (recreates the DB)
uv run python cli.py importar --tipo contratos --ano 2025
uv run python cli.py rag index             # build the RAG index (Chroma)
uv run python cli.py rag status

uv run uvicorn ui.server:app --port 8501   # landing (/) + chat (/chat) — add --reload in dev
uv run python -m ui                        # CLI chat (--once "pergunta" for one-shot)

uv run pytest -q                           # run the test suite
uv run ruff check . ; uv run ruff format . # lint / format
uv run alembic revision --autogenerate -m "msg" ; uv run alembic upgrade head
```

Docker: `docker compose build && docker compose up app` (the entrypoint runs
`db init`, `importar`, `rag index` then launches the FastAPI/Chainlit app via
uvicorn; disable with `AUTO_BOOTSTRAP_ON_START=0`). See `docs/docker.md`.

`importar` recreates the whole SQLite base before loading (POC behavior);
`--force` is kept only for compatibility.

## Architecture (request flow)

```
XML/CSV  → parser → Pydantic schema → SQLite           (ingestion, offline)
markdown/PDF → indexer → Chroma                         (RAG, offline)

user question
  → guardrails (agents/guardrails.py)                  block out-of-scope / empty / injection
  → deterministic policy (agents/chatbot/policy.py)    clarifications, protected acronyms, short follow-ups
  → hybrid selection (agents/chatbot/hybrid_selection.py)  narrow to a few candidate tools
  → LangChain agent (agents/chatbot/agent.py)          LLM orchestrates the selected tools
  → SQL tools + RAG tool → SQLite / Chroma → answer
```

## Directory map

- `cli.py` — Typer CLI: `db`, `importar`, `rag`.
- `ui/` — **user interfaces, kept separate so `agents/` stays UI-agnostic.**
  `server.py` (FastAPI: landing at `/` + mounts Chainlit at `/chat`), `chat_app.py`
  (Chainlit `on_chat_start`/`on_message` target), `errors.py` (`friendly_error_message`),
  `templates/` (Jinja2 landing) + `static/` (CSS/JS), `cli.py`
  (`run_once`/`run_interactive`), `__main__.py` (`python -m ui`). **`agents/` must
  never import `ui/`.**
- `agents/chatbot/` — chatbot core, framework/UI-agnostic:
  - `application.py` — `ChatbotApplication`, the conversation use case.
  - `backend.py` — `ChatbotAgentBackend`, runs the LangChain agent.
  - `_shared.py` — shared types (`ChatMessage`, `ChatResponse`, `ChatSession`, `AgentBackend`).
  - `core.py` — compatibility shim re-exporting the public API (imported by `ui/`, tests).
  - `agent.py` — agent bootstrap + `carregar_system_prompt()` (injects the current date).
  - `policy.py` — deterministic pre-model policy and clarification resolution.
  - `hybrid_selection.py` — hybrid tool selection (tool metadata + LLM selector + intent predicates).
  - `observability/` — pluggable provider (`noop` default / `langsmith`).
- `agents/guardrails.py` — hard-coded pre-model guardrails.
- `agents/nlu/` — natural-language understanding (replaced the removed `agents/routing/`):
  `reading.py` (`read_query`/`QueryReading`), `extractors/` (a package split by
  scope: `text`, `public_object`, `secretaria`, `historico`, `planejamento`,
  `contratos`, `receitas`; its `__init__` re-exports the flat `_extract_*` API),
  `detectors.py` (deterministic per-domain detectors), `intents.py` (intent
  predicates returning `ToolName`), `conversation.py`, `constants.py` (scope
  keywords), `models.py` (`GuardrailDecision`).
- `agents/tools/` — `registry.py` (`@register` decorator, scope/tags/routing
  metadata, discovery), **`names.py` (`ToolName` enum — single source of truth)**,
  `sql_tools/<domain>/` (one folder per domain), `rag_tools/`.
- `agents/rag/` — `indexing.py`, `retrieval.py`, `scope.py`, `config.py`.
- `ingestion/` — `pipeline.py` (orchestrator), `loaders/sql_loader.py` (batched
  upsert), `parsers/{xml,csv}/`, `schemas/` (Pydantic), `modules/` (per-`tipo`
  adapters).
- `database/` — `models/`, `session.py` (`get_session`), `migrations/`.
- `shared/` — `utils/` (`validation.py`, `dates.py`, `decimal_to_float.py`,
  `text.py`), `runtime_config.py` (paths + env). Cross-subsystem helpers only.
- `data/` — `xml/` (sources), `rag/{md,pdf}/` (curated corpus); `vector_store/`
  (generated Chroma index); `database/` (generated SQLite).

## Key architecture decisions (the non-obvious parts)

- **No deterministic router.** The legacy `agents/router.py` + `agents/routing/`
  (RouteDecision, ROUTE_PRIORITY_CHAIN, per-domain routes) was removed. **Tool
  routability comes from each tool's `routing_metadata`** (`examples`/`hints`/
  `exclusions`) consumed by the hybrid selector — adding a selectable public tool
  needs no central keyword chain. Only a few genuinely-ambiguous distinctions are
  kept as deterministic, test-locked predicates in `agents/nlu/intents.py`
  (emenda vs. transfer, list vs. aggregate spend-by-function, contract value-rank
  vs. count-rank, stock metrics).
- **`ToolName` (`agents/tools/names.py`) is the single source of truth for tool
  names.** It is a `StrEnum` (members are real strings). Every `@register(name=…)`
  and the whole selection layer reference it. `tests/tools/test_tool_names.py`
  asserts the enum and the registry are identical — **when you add/rename/remove a
  public tool, update `ToolName` or that test fails.** There are 31 public tools.
- **One public tool per broad capability.** Variations (filters, ordering,
  aggregation, field projection) are absorbed by the existing tool, not new tools.
  Per domain: `consultar_*` (lookup) + `agregar_*` (aggregate); special tools only
  for truly distinct shapes (e.g. `buscar_historico_de_pagamentos_do_servidor`).
  See `docs/arquitetura-agent-tools.md`.
- **Public tools must declare routing metadata.** Registering a `PUBLIC_SCOPE`
  tool without non-empty `examples` and `hints` raises at import time.
- **System prompt lives in `docs/agent-system-prompt.md`**, loaded at runtime by
  `carregar_system_prompt()`. The current date is appended via
  `shared/utils/dates.py` (`build_current_date_prompt_block`) so the LLM can
  resolve relative dates ("hoje", "ontem", "mês passado"). Editing that file
  changes live behavior; several `tests/agents/test_chatbot.py` tests assert prompt
  substrings.
- **Database model:** integer autoincrement `id` + `criado_em`/`atualizado_em`;
  monetary values are `Numeric(15,2)` (never `Float`); dates are `Date`;
  uniqueness via composite `UniqueConstraint`. Full schema in `docs/database.md`.

## Conventions & gotchas

- `from __future__ import annotations` is used throughout; annotations are not
  evaluated at runtime, so `TYPE_CHECKING` forward-refs are safe to avoid import
  cycles.
- Ingestion encoding: XML readers honor BOM + the declared `encoding` (fallback
  `ISO-8859-1`); CSV exports use `ISO-8859-1`. Parsers normalize money to `Decimal`
  and dates to `YYYY-MM-DD`. See `docs/importacao.md`.
- Shared-helper placement: `shared/` only for genuinely cross-subsystem helpers;
  otherwise a local `shared/` inside the subsystem. See `docs/shared-helpers.md`.
- The repo has a pre-existing baseline of Ruff `I001` (import-ordering) findings
  that are not enforced — don't chase them across files you aren't otherwise
  touching. Do keep new/edited files clean (`ruff check --fix` on what you touch).
- Always run `uv run pytest` (and `ruff check`) before finishing; keep the suite
  green at each step.
- Git: branch before committing if on `main`; end commit messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Testing

`pytest`. Notable suites: `tests/agents/test_chatbot.py` (pre-model boundary +
conversation contract), `tests/agents/test_guardrails.py` (scope/injection),
`tests/agents/test_hybrid_selection.py` + `tests/agents/test_intents.py`
(selection + intent predicates), `tests/tools/test_tool_names.py` (enum↔registry),
`tests/tools/test_registry.py`, `tests/nlu/` (extractors), `tests/parsers/`,
`tests/pipeline/`, `tests/loaders/`, `tests/ui/`. Manual end-to-end question set:
`docs/perguntas-teste-agente.md`.

## Configuration

`.env` (see `docs/configuration.md`): `DATABASE_URL`, `LLM_PROVIDER=openai`,
`OPENAI_MODEL`, `OPENAI_API_KEY` (required). Optional observability:
`OBSERVABILITY_ENABLED`, `OBSERVABILITY_PROVIDER` (`noop`|`langsmith`),
`LANGSMITH_*`. Docker overrides: `DOCKER_PORT`, `DOCKER_DATABASE_URL`,
`DOCKER_RAG_PERSIST_DIRECTORY`, `AUTO_BOOTSTRAP_ON_START`.

## Agent skills

### Issue tracker

Issues are tracked as GitHub issues in `thenriquedb/arcos-transparente` via the
`gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See
`docs/agents/domain.md`.
