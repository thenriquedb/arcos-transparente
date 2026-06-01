## Context

The repository already stores some `diárias`-related fields inside the broader `despesas` model: `objetivo_viagem`, `destino`, `data_inicial_viagem`, `data_final_viagem`, `quantidade_dias_diarias`, `valor_diaria`, and `valor_total` are present in the ingestion schema and SQL model, and the router can currently interpret a query like `Quanto foi pago em diarias em 2025?` as a `despesas` aggregation filtered by textual description. That means the project has partial support for per-diem data, but not an explicit contract for dedicated `diarias` CSV source files or a first-class tool surface for travel-specific questions.

The repository also has no existing CSV ingestion layer under `ingestion/parsers/`; current structured imports are XML-centric. Supporting `diarias` in CSV therefore requires both a format-aware ingestion addition and a clean reuse of the existing SQL/agent stack.

The current gaps are cross-cutting:

- file discovery only recognizes broad `despesas` patterns such as `empenhos`, `restos-a-pagar`, and `documentos-extras`
- the parser does not declare a dedicated `diarias` source profile even though the canonical model already contains travel fields
- public SQL tooling exposes only generic `despesas` fields, not a travel-oriented lookup/aggregation surface
- agent routing and prompt contracts still treat `diárias` as a heuristic flavor of `despesas`, not as an explicit supported tool path

The change therefore needs to connect ingestion, persistence, public tools, and agent orchestration around one consistent diárias contract.

## Goals / Non-Goals

**Goals:**
- Make supported `diarias` CSV files discoverable and importable through the standard local ingestion flow.
- Persist imported `diarias` records in the SQL database with their travel-specific fields preserved and queryable.
- Provide dedicated public `diarias` tools for list and aggregation questions, backed by the local SQL data.
- Update router and prompt/tool contracts so the chatbot uses the dedicated `diarias` tool path for supported per-diem questions.
- Add end-to-end regression coverage from CSV import through public tool and agent behavior.

**Non-Goals:**
- Replacing the broader `despesas` domain or migrating all expense logic to a separate `diarias` subsystem.
- Building a second storage database just for travel allowances.
- Inferring or fabricating travel metadata that is not present in the imported CSV rows.
- Reworking unrelated transparency domains such as receitas, contratos, or folha de pagamento.

## Decisions

### 1. Treat dedicated `diarias` CSV as an explicit source profile and add a minimal CSV ingestion path

The ingestion pipeline should recognize supported `diarias` CSV files as their own source profile, matched by explicit filename rules and header/schema expectations. Because the codebase currently only has XML parsers, this change should introduce a minimal CSV parser area for `diarias`, rather than trying to squeeze CSV handling into the XML parser stack.

Rationale:
- `diárias` is already modeled as a kind of expense data in the project.
- Source-profile matching makes new file support visible and testable.
- Adding a small CSV-specific parsing path is the lowest-risk way to support the real file format without distorting the existing XML abstractions.

Alternatives considered:
- Keep folding `diarias` into generic `despesas` discovery only by keyword or text content: rejected because dedicated source files would remain implicit and fragile.
- Parse CSV through the XML parser area with format branches: rejected because it would blur format boundaries and make the ingestion layer harder to maintain.
- Create an entirely separate ingestion pipeline disconnected from the expense flow: rejected because it would duplicate infrastructure for a closely related dataset.

### 2. Reuse `DespesaDocumento` as the canonical SQL backbone for diárias, extending it only where necessary

Imported `diarias` records should persist into the existing expense-document model, using a canonical source subtype such as `tipo_origem=\"diaria\"` or an equivalent explicit discriminator. Existing travel fields should remain the primary storage target. If the new CSV introduces stable, citizen-facing fields not covered today, the change may extend the model through migrations, but it should avoid creating a second top-level diárias table unless the source structure fundamentally requires it.

Rationale:
- The schema already has travel/per-diem columns, which strongly suggests the intended canonical home.
- Reusing the existing model keeps joins, migrations, and public querying simpler.
- It preserves a unified financial-data lineage for auditability.

Alternatives considered:
- Create a separate `diarias` parent table immediately: rejected because it would split a domain that the current schema already partially supports.
- Store raw CSV rows only and derive travel fields at query time: rejected because it weakens filtering and makes tools harder to reason about.

### 3. Use file-plus-row lineage as the default idempotency contract for CSV imports

Because CSV feeds often lack a durable single-record identifier, the default import contract should use the source file plus row sequence, unless the actual file schema provides a stronger stable business key. The normalization layer should also preserve enough row metadata to make debugging and re-import behavior auditable.

Rationale:
- This matches how the current expense import stack already thinks about deterministic source lineage.
- It gives us a predictable first implementation even if the CSV does not ship a canonical unique ID.
- It keeps re-import semantics explicit instead of pretending stronger deduplication exists.

Alternatives considered:
- Require a business key before any import support: rejected because many public CSV exports do not provide one cleanly.
- Deduplicate heuristically on text/value combinations only: rejected because that is fragile and hard to explain.

### 4. Add dedicated public `diarias` tools instead of overloading generic `despesas` tools further

The agent-facing contract should include dedicated public tools such as a lookup tool and an aggregation tool for diárias. Those tools can be implemented on top of the same canonical SQL rows, but they should expose travel-specific filters and fields explicitly, such as destination, trip dates, quantity of daily allowances, unit value, total value, and beneficiary/creditor.

Rationale:
- Users ask diárias questions with travel-specific intent that generic `despesas` tools do not express well.
- A dedicated tool contract makes prompt guidance, router behavior, and testing clearer.
- It reduces dependence on vague text filters like `descricao = diaria`.

Alternatives considered:
- Keep using only `consultar_despesas` and `agregar_despesas`: rejected because the current public field set hides much of the travel structure.
- Create many narrowly scoped diárias tools per question type: rejected because a small lookup/aggregate pair is easier for the agent to use reliably.

### 5. Update routing and prompt contracts to prefer the `diarias` domain for structured per-diem questions

When the user asks structured questions about travel allowances, the router compatibility layer and the chatbot prompt should prefer the dedicated `diarias` tools as the SQL source of truth. The older `despesas` fallback can remain available for broad expense questions, but diárias-specific queries should no longer depend on a generic expense path alone.

Rationale:
- The agent is more reliable when domain boundaries are explicit.
- Dedicated tool routing improves auditability of how answers were produced.
- This change aligns user language (`diárias`) with the public tool surface.

Alternatives considered:
- Rely only on the model to choose the right tool from the registry: rejected because explicit routing already exists for high-confidence transparency queries.
- Keep the existing router heuristics unchanged and only add tool registration: rejected because the current heuristics would continue steering `diárias` into the generic expense domain.

### 6. Require end-to-end regression coverage with dedicated `diarias` CSV fixtures

The change should add parser, pipeline, tool, and router/chatbot tests using at least one representative dedicated `diarias` CSV sample. The acceptance bar is not just successful parsing, but successful answerability through the new public tool contract.

Rationale:
- The major risk is integration drift between import, persistence, tool schemas, and routing.
- Existing `diárias` coverage today proves a fallback behavior, not the dedicated-file workflow requested here.

Alternatives considered:
- Test only the parser and trust the rest of the stack: rejected because agent integration is part of the requested change.
- Test only the tools with fabricated database rows: rejected because it would not prove that new source files actually load correctly.

## Risks / Trade-offs

- [Risk] Dedicated `diarias` CSV files may diverge from the existing `despesas` field model more than expected. -> Mitigation: implement explicit source-profile normalization and promote only stable, queryable new fields into the canonical schema.
- [Risk] CSV headers, delimiters, encodings, or localized number/date formats may vary across deliveries. -> Mitigation: centralize CSV reading/normalization rules and cover representative fixtures in tests.
- [Risk] Adding dedicated `diarias` tools could create overlap with the existing `despesas` tools. -> Mitigation: keep clear routing and prompt guidance that `diarias` tools are the preferred surface for travel-allowance questions while `despesas` remains the broader expense domain.
- [Risk] Reusing the `DespesaDocumento` table may leave some columns sparse across non-diárias records. -> Mitigation: accept sparsity as a trade-off for a unified canonical model and add only fields with clear citizen-facing value.
- [Risk] Re-import behavior may still depend on file-plus-row lineage if the source system lacks a stronger stable identifier. -> Mitigation: document the idempotency contract explicitly and revisit stronger deduplication only if the CSV provides trustworthy identifiers.

## Migration Plan

1. Identify the supported dedicated `diarias` file patterns, delimiter/header contract, and column mappings to treat as first-class source profiles.
2. Introduce a minimal CSV parser/reader path and extend the normalization contract so those rows map into canonical expense/diárias fields.
3. Add any required migration changes for new stable travel-specific fields or discriminator values.
4. Update the ingestion pipeline to discover and load dedicated `diarias` files through the standard import flow.
5. Add public `consultar_diarias` and `agregar_diarias`-style tools backed by the persisted SQL subset.
6. Update routing and chatbot prompt/tool guidance so structured per-diem questions use the new tool path.
7. Add regression tests for discovery, parsing, persistence, tool responses, and representative agent queries.

Rollback strategy:
- Disable the dedicated `diarias` source profile if the new file layout proves unstable while leaving the rest of the expense ingestion stack intact.
- Remove or hide the dedicated public tools and route `diárias` queries back through the broader `despesas` domain if needed.
- Revert any new schema migration and reimport using only the previously supported flows.

## Open Questions

- What exact filename patterns, delimiter/encoding, headers, and field names do the new dedicated `diarias` CSV files use?
- Are there trip-specific audit columns in the new CSV files that are not represented in `DespesaDocumento` today?
- Should the first public `diarias` tool version expose only the most important travel fields, or all persisted travel-specific fields immediately?
