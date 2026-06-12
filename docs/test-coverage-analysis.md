# Test Coverage Analysis — Arcos Transparente

Scope: the whole repo (433 tests). This report is specific to *this* codebase —
file/function names are real and were inspected. Where coverage exists
indirectly, it is called out explicitly. Assumptions are flagged with **(assumption)**.

---

## Existing coverage summary

What is **already well covered**:

- **XML ingestion encoding** (`ingestion/parsers/xml/shared.py`) — `tests/parsers/test_xml_shared.py` (8 tests) covers ISO-8859-1, declared UTF-8, BOM, fallback, **invalid declared encoding → `ValueError`**, declared-encoding/bytes mismatch → `ValueError`, and control-char sanitization. Strong.
- **Per-domain parsers** (`tests/parsers/*`) and **per-domain pipeline happy paths** (`tests/pipeline/*`) — each `tipo` has at least one parse + load-to-SQLite test.
- **Per-domain public SQL tools** (`tests/tools/sql_tools/*`, ~120 tests) — filtering, aggregation, pagination, field projection, and per-domain quirks (e.g. estoque flow metrics, contract value-zero fallback). `validate_tool_params` **invalid-input → structured error** is covered for several domains (servidores, licitacoes, receitas, planejamento, eleitos).
- **Tool selection** — `tests/agents/test_hybrid_selection.py` (30) + `tests/agents/test_intents.py` lock the deterministic heuristics; `tests/tools/test_tool_names.py` enforces the `ToolName`↔registry single-source-of-truth.
- **Guardrails / deterministic policy** — `tests/agents/test_guardrails.py` + the large `tests/agents/test_chatbot.py` (77) cover scope/injection blocking, protected-acronym and bus-type clarification flows, elliptical follow-ups, and the system-prompt contract (incl. current-date injection).
- **NLU extractors** — `tests/nlu/test_extractors.py` covers limit/secretaria/planejamento alias extraction.
- **RAG** — `tests/rag/test_markdown_knowledge.py` (10) covers index build/manifest/`ready`/`stale`/rebuild, status `missing`/`empty`, grounded retrieval, lexical priority, miss-vs-missing-index, scope gating, and the Chroma runtime fallback.
- **Validation utils / dates** — `tests/shared/test_validation.py` (14) + `tests/shared/test_dates.py` (5).
- **Observability happy path** — `tests/agents/test_chatbot_observability.py` (7): noop/langsmith config, missing-key rejection, span emission for blocked/allowed queries, error surfaced on the request span. The **top-level `api_key → [REDACTED]`** redaction is covered indirectly via `tests/tools/test_registry.py::test_wrapper_publico_emite_observabilidade_com_argumentos_sanitizados`.
- **Backend happy paths** — agent reuse/thread-id and one streaming happy path (`FakeAgent` yielding model-node chunks) in `tests/agents/test_chatbot.py`.

What has **no dedicated test module**: `agents/chatbot/streaming.py`, `agents/chatbot/observability/sanitization.py` (beyond the one indirect case), `database/session.py` pragmas, `ui/web.py` error UX.

---

## Critical missing scenarios

### C1 — SQL loader transaction integrity, error isolation, and type validation
- **Why critical:** `ingestion/loaders/sql_loader.py::SQLLoader.load` is the ACID core of every import. Its three existing tests (`tests/loaders/test_sql_loader.py`) only cover the happy insert, in-batch duplicate, text sanitization, and matrícula dedup. The transaction/validation logic is the part most likely to silently corrupt data.
- **What could break in production:**
  - A malformed record in a batch should bump `erros += 1` and **continue** (per-record `except Exception`, ~L80); a regression could abort the whole batch or crash the import.
  - A DB-level failure should `rollback()` the **entire batch** and add `erros += len(batch)` (`except SQLAlchemyError`, ~L85). A regression could half-commit a batch → partial/inconsistent data.
  - `_normalize_and_validate` is the type firewall: monetary value as `str` → `TypeError`, non-Decimal/int money → `TypeError`, bad date → `TypeError`, non-str text → `TypeError`, missing/null required field → `ValueError`, missing unique-constraint field → `ValueError`. None of these rejections is tested — a loosened check could let `Float`/bad money into the DB.
  - The **update branch** (`_apply_updates` → `atualizados`) and "no change → `ignorados`" are untested (only insert/dedup are).
  - Batch boundary: `batch_size` splitting (e.g. 250 rows / size 100 → 3 batches) is untested.
  - Model without `UniqueConstraint` → `ValueError` (`_build_unique_filter`) untested.
- **Involved:** `ingestion/loaders/sql_loader.py` (`load`, `_normalize_and_validate`, `_build_unique_filter`, `_apply_updates`, `_find_duplicate_before_insert`).
- **Test type:** unit/integration with an in-memory SQLite session and small purpose-built models (or `Servidor`/a child model), asserting `LoadResult` counters and persisted rows per scenario.

### C2 — Observability payload sanitization edge cases (credential / PII leak prevention)
- **Why critical:** `agents/chatbot/observability/sanitization.py` is the **only thing** standing between runtime payloads (tool args, results, errors, history) and an **external service (LangSmith)**. Only the single top-level `api_key` case is exercised today.
- **What could break in production:** a regression could ship secrets or citizen PII off-box. Untested behaviors: nested sensitive keys (`{"headers": {"authorization": ...}}`), the `_SENSITIVE_KEYWORDS` set (`auth`, `password`, `secret`, `token`, `apikey`), `sanitize_mapping(allowed_keys=...)` allowlist filtering (events are supposed to be allowlisted), `_MAX_DEPTH`/`<max-depth>`, `_MAX_ITEMS` list truncation, `_MAX_STRING_LENGTH` truncation, and `float('nan'/'inf') → None`.
- **Involved:** `sanitization.py` (`sanitize_mapping`, `sanitize_value`, `summarize_result`, `sanitize_error`, `_looks_sensitive`, `_truncate`).
- **Test type:** unit. Pure functions, cheap, high value.

### C3 — Hybrid selector resilience when the LLM misbehaves
- **Why critical:** `HybridToolSelector.select` (`agents/chatbot/hybrid_selection.py`) wraps a **real network LLM call** (`_run_model_selector` → `model.invoke`). In production the model **will** occasionally time out, error, or return non-JSON. The safe-fallback branches are the resilience layer and are untested.
- **What could break in production:** the existing tests cover the low-confidence fallback and the unknown-tool-name fallback, but **not**: runner raises → `selector_error` fallback to the full public surface; uncoercible runner output → `invalid_selector_output` fallback; `clarify` action without `user_message` → `missing_selector_message` fallback; empty catalog → `empty_catalog`. A regression here turns a transient LLM error into a hard request failure (the chatbot breaks instead of degrading to the full tool set).
- **Involved:** `hybrid_selection.py` (`select`, `_fallback_selection`, `_coerce_selector_payload`, `_resolve_allow_selection`).
- **Test type:** unit, injecting a `runner` that raises / returns `12345` / returns a malformed mapping / returns `clarify` with no message; assert `used_fallback` and `reason_code`.

### C4 — Streaming: fallback chain + tool/system-message filtering + content blocks
- **Why critical:** streaming is the **primary user-facing UX** (Streamlit). `agents/chatbot/backend.py::stream_answer_with_selection` and `agents/chatbot/streaming.py` parse arbitrary LangGraph events. Only the all-happy path (model-node chunks, plain-string content) is tested.
- **What could break in production:**
  - Fallback branches are untested: agent has no `.stream` → `stream_not_supported` → fall back to `answer`; `.stream` raises `TypeError` → `stream_type_error` → fall back; stream yields nothing → `empty_stream` → fall back. A regression yields an **empty reply** to the user.
  - `streaming.py::_is_user_visible_stream_message` is what keeps **tool/internal messages out of the user stream**. Untested — a regression could stream raw tool output or system text to citizens.
  - `streaming.py::content_to_text` for **list/dict content blocks** (LangChain returns these, not just `str`) is untested; only `FakeChunk.content = str` is exercised. This is exactly the kind of thing that breaks on a LangChain/LangGraph version bump.
- **Involved:** `backend.py` (stream fallbacks), `streaming.py` (`extract_stream_chunk_content`, `content_to_text`, `_is_user_visible_stream_message`, `_is_langgraph_message_event`).
- **Test type:** unit with fake agents/events covering each branch; regression test for content-block shapes.

### C5 — Database engine pragmas and foreign-key enforcement
- **Why critical:** `database/session.py::_apply_sqlite_pragmas` sets `journal_mode=WAL`, **`foreign_keys=ON`**, `synchronous=NORMAL`. SQLite defaults `foreign_keys=OFF`. This is never asserted, **and every pipeline/tool test builds its own `create_engine("sqlite:///:memory:")` without this connect-event** — so the production engine config is exercised by zero tests.
- **What could break in production:** if `foreign_keys=ON` were dropped/regressed, FK constraints would silently stop enforcing (orphan child rows, broken `fornecedor_id` links) and **no test would catch it**. Also `_ensure_sqlite_storage_directory` (creates the SQLite parent dir) is untested — a deploy with a fresh volume path could fail at startup.
- **Involved:** `database/session.py` (`_apply_sqlite_pragmas`, `_ensure_sqlite_storage_directory`, `get_session`).
- **Test type:** integration — open a connection from the real `engine` and assert `PRAGMA foreign_keys`/`journal_mode`; a separate test that inserts an orphan child under an FK-enabled engine and expects an `IntegrityError`.

### C6 — Web error UX (`ui/web.py`)
- **Why critical:** the chatbot core **re-raises** backend exceptions (verified: `application.py`/`backend.py` record the error span and re-raise); the only place they become user-friendly is `ui/web.py::handle_prompt` + `friendly_error_message`. None of the error branches are tested (`tests/ui/test_web.py` covers happy render, `$` escaping, code spans, session recreation).
- **What could break in production:** the mapping of `OPENAI_API_KEY`/`OPENAI_MODEL` errors, unsupported-provider errors, and SQLite errors (`no such table`, `database is locked`, `transparencia.db`) to friendly guidance — plus `ValueError → st.warning` vs generic `Exception → st.error` + "Detalhes técnicos" expander. A regression shows citizens a raw stack trace or wrong instructions.
- **Involved:** `ui/web.py` (`handle_prompt`, `friendly_error_message`).
- **Test type:** unit (monkeypatch `st`, raise each error class, assert the rendered message + that nothing is appended to history on hard failure).

### C7 — `importar` destructive recreate side effect
- **Why critical:** `cli.py::_recriar_base_importacao` (assumption: it drops+recreates the schema) runs on **every** `importar`, and the Docker entrypoint runs `importar` on each container start. This is a destructive state transition.
- **What could break in production:** a regression that fails to recreate cleanly (or recreates partially) corrupts the base that the chatbot then serves; under `AUTO_BOOTSTRAP_ON_START=1` this happens automatically on deploy.
- **Involved:** `cli.py` (`_recriar_base_importacao`, `importar`).
- **Test type:** integration with a temp DB URL: seed rows → `importar` → assert old rows gone and new rows present; assert it’s idempotent across two runs.

---

## Priority ranking

| # | Scenario | Risk | Impact | Likelihood of regression | Priority |
|---|----------|------|--------|--------------------------|----------|
| C1 | SQL loader rollback / validation / update path | High (data corruption) | High | Med (complex branchy code) | **P0** |
| C2 | Sanitization secret/PII leak edge cases | High (security/LGPD, external service) | High | Med | **P0** |
| C3 | Hybrid selector LLM-failure fallbacks | Med-High (chatbot outage) | High | High (LLM is flaky by nature) | **P0** |
| C4 | Streaming fallbacks + tool-msg filtering + content blocks | Med-High (UX / data leak in stream) | High | High (version-bump fragile) | **P1** |
| C5 | DB pragmas + FK enforcement | Med (silent integrity loss) | Med-High | Low-Med | **P1** |
| C6 | Web error UX | Med (poor UX, confusing failures) | Med | Med | **P1** |
| C7 | `importar` destructive recreate | Med (deploy-time data loss) | High | Low | **P2** |

---

## Recommended next tests to implement first

Ordered for best risk-reduction per effort:

1. **`tests/loaders/test_sql_loader_errors.py` (C1, P0)** — batch rollback on `SQLAlchemyError`; per-record error isolation (one bad record, rest persist); each `_normalize_and_validate` rejection (money-as-string, bad date, missing required, missing unique field); update vs ignored counters; multi-batch boundary. *Pure infra, cheap, highest data-integrity payoff.*
2. **`tests/agents/test_sanitization.py` (C2, P0)** — nested sensitive-key redaction, each `_SENSITIVE_KEYWORDS` term, `allowed_keys` allowlist drop, `_MAX_DEPTH`, `_MAX_ITEMS`, `_MAX_STRING_LENGTH`, NaN/inf → None. *Pure functions; protects credentials/PII leaving the box.*
3. **Extend `tests/agents/test_hybrid_selection.py` (C3, P0)** — runner raises → `selector_error`; uncoercible output → `invalid_selector_output`; `clarify` w/o message → `missing_selector_message`; empty catalog. *Locks the resilience layer against real LLM flakiness.*
4. **`tests/agents/test_streaming.py` + backend stream-fallback tests (C4, P1)** — `content_to_text` for list/dict content blocks; `_is_user_visible_stream_message` filters tool/non-model nodes; backend fallback when `.stream` is absent / raises `TypeError` / yields nothing.
5. **`tests/test_session_pragmas.py` (C5, P1)** — assert `foreign_keys=ON`/`journal_mode=WAL` on a real connection; assert an FK violation raises under an FK-enabled engine; assert `_ensure_sqlite_storage_directory` creates a missing parent dir.
6. **Extend `tests/ui/test_web.py` (C6, P1)** — each `friendly_error_message` branch; `ValueError → warning` vs `Exception → error`; history not appended on hard failure.

---

## Fragile areas — where current tests create a false sense of safety

- **In-memory engines bypass production DB config.** Every `tests/pipeline/*` and `tests/tools/sql_tools/*` test builds its own `create_engine("sqlite:///:memory:")` with no connect-event, so they run with **`foreign_keys=OFF`**. Green tests do **not** prove FK integrity or that the production pragmas in `database/session.py` work. (C5)
- **Hybrid-selection tests stub a well-behaved runner.** The 30 selector tests inject clean dicts or assert the heuristic short-circuits, so they validate the *happy* selection path — not the *actual* production failure mode (a flaky/garbage-returning LLM). The fallback branches look "implicitly covered" but are not. (C3)
- **Streaming "covered" only for the ideal shape.** The one streaming backend test uses `FakeChunk.content = str` on a `model` node. It gives the impression streaming is tested, but the parts that historically break — tool/system-message filtering and non-string content blocks — are not exercised. (C4)
- **Sanitization "covered" by a single case.** The lone `api_key → [REDACTED]` assertion in `test_registry.py` can read as "secret redaction is tested", while nested keys, allowlisting, depth, truncation, and value-level PII are not. (C2)
- **Chatbot error handling is split across layers.** The core re-raises and only the UI makes errors friendly; tests assert the core records an error span but never assert the user-facing outcome, so a broken `friendly_error_message` would pass CI. (C6)
- **Loader counters tested only on success paths.** `LoadResult.inseridos`/dedup are asserted, but `atualizados`/`erros` (the counters that signal data problems in production logs) are essentially unverified. (C1)
