## 1. Diarias Source Ingestion

- [x] 1.1 Identify the supported dedicated `diarias` CSV filename patterns, delimiter/header contract, and extend ingestion file discovery to include them.
- [x] 1.2 Add a minimal CSV parsing and normalization flow for `diarias` that emits canonical SQL-ready records with travel-specific fields and an explicit source subtype.
- [x] 1.3 Add representative `diarias` CSV fixtures and parser-level regression tests for valid and unsupported source layouts.

## 2. SQL Persistence

- [x] 2.1 Extend the SQL model and migration layer for any new `diarias` discriminator values or stable travel-specific fields required by the new files.
- [x] 2.2 Update the ingestion load path so imported `diarias` rows upsert idempotently by file-plus-row lineage and preserve the supported travel-specific attributes in the local database.
- [x] 2.3 Add pipeline/database regression tests proving dedicated `diarias` files persist correctly and remain stable across re-imports.

## 3. Public Diarias Tools

- [x] 3.1 Implement a dedicated public lookup tool for `diarias` with travel-oriented filters, projected fields, and response metadata.
- [x] 3.2 Implement a dedicated public aggregation tool for `diarias` with supported totals, counts, and ranking/grouping behavior.
- [x] 3.3 Register the new `diarias` tools in the public tool registry and add unit tests for their SQL-backed query behavior.

## 4. Agent Integration

- [x] 4.1 Update query routing and public tool selection so structured `diarias` questions prefer the dedicated `diarias` tool path over generic `despesas` fallbacks.
- [x] 4.2 Update chatbot prompt and tool descriptions so the agent treats `diarias` as an explicit SQL transparency domain.
- [x] 4.3 Add end-to-end router/chatbot regression tests showing imported `diarias` data is reachable through the dedicated public tools.
