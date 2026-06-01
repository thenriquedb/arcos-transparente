## Context

The repository already imports several transparency domains into local SQL, and the `despesas` pipeline now includes XML sources plus a minimal CSV path for `diarias`. There is also a real `passagens` source file at `data/xml/despesas/passagens/passagens-2026.csv`, but no current file discovery rule, parser, SQL subtype, public tool, or routing contract for it. As a result, structured questions about airfare or locomotion expenses cannot be answered from the local database even though the raw data has arrived.

The available `passagens` CSV is structurally similar to the current `diarias` CSV pattern:

- ISO-8859-1 encoded
- semicolon-delimited
- metadata preamble with `Exercicio`, `Periodo`, `Unidade Gestora`, and transfer/category information
- consolidated rows by beneficiary with canonical payment columns such as `Valor Empenhado`, `Valor Liquidado`, and `Valor Pago`

That similarity creates a low-risk path: extend the existing CSV ingestion style and reuse the current SQL/agent architecture rather than inventing a new subsystem. The main design challenge is to keep the contract explicit enough that `passagens` becomes a first-class domain for the agent while still fitting into the broader `despesas` ingestion backbone.

## Goals / Non-Goals

**Goals:**
- Make supported `passagens` CSV files discoverable and importable through the standard local `despesas` ingestion flow.
- Persist imported `passagens` records in SQL with the source-backed period, beneficiary, origin, category, and monetary fields needed for public queries.
- Provide dedicated public `passagens` lookup and aggregation tools backed by local SQL.
- Update routing and prompt/tool contracts so the chatbot prefers the dedicated `passagens` tool path for supported questions.
- Add end-to-end regression coverage from CSV import through public tool and agent behavior.

**Non-Goals:**
- Replacing the broader `despesas` domain or creating a separate storage database just for `passagens`.
- Inferring ticket-level details such as route, destination, reservation code, or passenger purpose when those values are absent from the CSV.
- Building a combined `diarias + passagens` analytics domain in this change.
- Reworking unrelated transparency domains such as receitas, contratos, or folha de pagamento.

## Decisions

### 1. Treat dedicated `passagens` CSV as an explicit source profile and reuse the minimal CSV ingestion layer

The ingestion pipeline should recognize supported `passagens` CSV files by explicit filename and header/schema rules, using the same shared CSV reading helpers already introduced for `diarias`. The parser should live in the CSV parser area and normalize rows into SQL-ready payloads instead of mixing CSV behavior into the XML parser stack.

Rationale:
- The real source already matches a known CSV ingestion style in the repo.
- Explicit source-profile matching makes support visible, testable, and auditable.
- Reusing the existing helpers keeps encoding and cell-cleanup rules consistent.

Alternatives considered:
- Keep `passagens` as an unsupported file sitting beside `despesas`: rejected because the user explicitly wants it imported and agent-accessible.
- Parse the CSV through XML-specific abstractions: rejected because it blurs format boundaries and increases maintenance cost.
- Build a separate ingestion command just for `passagens`: rejected because it duplicates the existing `despesas` import workflow.

### 2. Reuse `DespesaDocumento` as the canonical SQL backbone for `passagens`

Imported `passagens` rows should persist into `despesa_documentos` with an explicit discriminator such as `tipo_origem="passagem"`, using existing shared fields for source lineage, beneficiary, document date, report period, category, and monetary values. Because the current source is consolidated and does not expose itinerary-specific fields, the first version should avoid adding new `passagens`-only columns unless a stable, source-backed attribute clearly requires one.

Rationale:
- The current row shape fits the existing expense-document schema.
- Reusing the same table keeps migrations, generic expense reporting, and local query plumbing simpler.
- It preserves a consistent audit trail across expense-like sources.

Alternatives considered:
- Create a separate `passagens` parent table immediately: rejected because the available CSV does not yet justify a split from the broader expense-document storage model.
- Store only raw CSV rows and interpret them at query time: rejected because it weakens structured querying and tool clarity.

### 3. Use file-plus-row lineage as the default idempotency contract

The current `passagens` CSV does not expose an obvious stable record identifier, so imports should deduplicate and update rows by source file plus row sequence unless a stronger business key appears in future deliveries. The normalized payload should preserve enough metadata to explain where each SQL row came from.

Rationale:
- This matches the existing import style for consolidated CSV datasets.
- It is deterministic and easy to test.
- It avoids pretending the source has stronger identity guarantees than it does.

Alternatives considered:
- Require a stable external ID before supporting import: rejected because the available file does not provide one.
- Deduplicate on beneficiary plus values alone: rejected because that is fragile across corrections and repeated periods.

### 4. Add dedicated public `passagens` tools with a source-backed field contract

The agent-facing surface should include dedicated public tools such as `consultar_passagens` and `agregar_passagens`, implemented on top of persisted SQL rows but limited to fields the CSV actually provides: beneficiary/credor, CPF/CNPJ, origin, exercise, period, category, and monetary values. The tool contract should not imply itinerary details that the source does not contain.

Rationale:
- Users ask `passagens` questions with domain-specific intent that generic `despesas` tools do not express clearly.
- A dedicated tool surface improves prompt guidance, router behavior, and testability.
- Keeping the field contract source-backed avoids misleading answers.

Alternatives considered:
- Reuse only generic `consultar_despesas` and `agregar_despesas`: rejected because the agent would keep relying on fuzzy description filters instead of a clear domain path.
- Expose many narrowly scoped tools per metric: rejected because a small lookup/aggregate pair is easier for the agent to use reliably.

### 5. Prefer the `passagens` domain in routing and prompt contracts for structured queries

When a user asks structured questions about `passagens`, airfare, or locomotion spending, the router and chatbot prompt should prefer the dedicated `passagens` tools as the SQL source of truth. Generic `despesas` can remain available for broader expense questions, but `passagens` should become an explicit supported route.

Rationale:
- Clear domain routing improves answer reliability and auditability.
- It aligns user language with the public tool surface.
- It reduces dependence on generic keyword matching in the wider expense domain.

Alternatives considered:
- Let the model infer the correct tool without route help: rejected because the repo already uses explicit routing for high-confidence public-data questions.
- Keep existing routing unchanged and only register new tools: rejected because unsupported or generic routes would remain the default behavior.

### 6. Require end-to-end regression coverage with representative `passagens` fixtures

The acceptance bar should cover parser behavior, pipeline persistence, public SQL tools, and router/chatbot integration using at least one representative `passagens` CSV fixture based on the known file layout.

Rationale:
- The main risk is drift between import, storage, tools, and routing.
- Parser-only or tool-only tests would miss the user-visible integration contract.

Alternatives considered:
- Test only parser normalization: rejected because agent integration is part of the requested change.
- Test only tools with fabricated rows: rejected because it would not prove the real CSV becomes queryable through the supported pipeline.

## Risks / Trade-offs

- [Risk] Future `passagens` files may add columns or layout variations beyond the current sample. -> Mitigation: match explicit source profiles and centralize CSV normalization rules so support can be extended intentionally.
- [Risk] The consolidated source does not contain itinerary-level details that some users may ask for. -> Mitigation: keep the public field contract limited to source-backed attributes and document routing/tool expectations accordingly.
- [Risk] Dedicated `passagens` tools may overlap with generic `despesas` tooling. -> Mitigation: prefer dedicated routing for `passagens` questions while keeping generic tools for broader expense queries.
- [Risk] File-plus-row lineage may be weaker than a true business identifier. -> Mitigation: document the idempotency contract explicitly and revisit if future files provide a stable external key.
- [Risk] Reusing `despesa_documentos` could add another sparse subtype to the table. -> Mitigation: only store source-backed fields already supported by the canonical expense model unless a clearly valuable new field emerges.

## Migration Plan

1. Add a supported `passagens` source profile to `despesas` file discovery, backed by explicit filename and header validation.
2. Implement a CSV parser that normalizes consolidated `passagens` rows into canonical SQL-ready payloads.
3. Extend the persistence path so imported rows upsert into `despesa_documentos` with a `passagem` source discriminator and source-backed period/category fields.
4. Add dedicated public `consultar_passagens` and `agregar_passagens`-style tools backed by the persisted SQL subset.
5. Update routing, tool registration, and chatbot prompt guidance so structured `passagens` questions prefer the new domain path.
6. Add regression tests for discovery, parsing, persistence, public tool responses, and representative agent queries.

Rollback strategy:
- Remove the `passagens` source profile from discovery if the source layout proves unstable.
- Disable the dedicated public `passagens` tools and route those queries back to the broader unsupported/generic path if needed.
- Revert any schema migration or subtype wiring and reimport using only previously supported `despesas` sources.

## Open Questions

- Will future `passagens` deliveries include additional years or separate files by origin beyond the current `passagens-2026.csv` sample?
- Does the source authority intend `passagens` to remain consolidated by beneficiary, or are ticket-level exports expected later?
- Should the first public `passagens` contract expose only the default monetary fields, or also include raw report-category labels such as `Tipo da Transferencia` when present?
