## 1. Passagens Source Ingestion

- [x] 1.1 Identify the supported dedicated `passagens` CSV filename pattern, encoding, delimiter, header contract, and extend `despesas` file discovery to include it.
- [x] 1.2 Implement a CSV parsing and normalization flow for `passagens` that converts consolidated beneficiary/payment rows plus report metadata into canonical SQL-ready records.
- [x] 1.3 Add representative `passagens` CSV fixtures and parser-level regression tests for valid and unsupported source layouts.

## 2. SQL Persistence

- [x] 2.1 Wire imported `passagens` rows into the canonical SQL persistence path with an explicit source discriminator and the supported report-period/category fields.
- [x] 2.2 Add any required migration or schema adjustments only if the current expense model lacks a stable source-backed field needed by the `passagens` contract.
- [x] 2.3 Add pipeline/database regression tests proving dedicated `passagens` files persist correctly and remain stable across re-imports.

## 3. Public Passagens Tools

- [x] 3.1 Implement a dedicated public lookup tool for `passagens` with supported filters, projected fields, and response metadata limited to source-backed attributes.
- [x] 3.2 Implement a dedicated public aggregation tool for `passagens` with totals, counts, and ranking/grouping behavior over imported SQL data.
- [x] 3.3 Register the new `passagens` tools in the public tool registry and add unit tests for their SQL-backed query behavior.

## 4. Agent Integration

- [x] 4.1 Update query routing and public tool selection so structured `passagens` questions prefer the dedicated `passagens` tool path over generic `despesas` fallbacks.
- [x] 4.2 Update chatbot prompt and tool descriptions so the agent treats `passagens` as an explicit SQL transparency domain with a source-backed field contract.
- [x] 4.3 Add end-to-end router/chatbot regression tests showing imported `passagens` data is reachable through the dedicated public tools.
