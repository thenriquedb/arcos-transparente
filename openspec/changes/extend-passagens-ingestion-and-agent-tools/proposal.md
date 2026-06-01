## Why

The repository already imports several `despesas` sources and now has a real `data/xml/despesas/passagens/passagens-2026.csv` delivery, but there is no contract for discovering, loading, storing, or querying that dataset through the agent. We need an end-to-end `passagens` flow so airfare and locomotion spending can be answered from local structured data instead of remaining invisible to the import pipeline and public tool layer.

## What Changes

- Extend the local `despesas` ingestion flow to discover supported `passagens` CSV files and parse their consolidated payment rows.
- Persist imported `passagens` records in the SQL database with the report-period, beneficiary, origin, and monetary fields needed for public querying.
- Add dedicated public `passagens` lookup and aggregation tools for the agent, backed by the persisted SQL data.
- Update routing and prompt/tool contracts so structured questions about `passagens` prefer the dedicated public tool path instead of generic `despesas` fallback behavior.
- Add regression coverage for CSV parsing, persistence, tool queries, and agent routing over imported `passagens`.

## Capabilities

### New Capabilities
- `passagens-source-ingestion`: Discovers supported `passagens` CSV files, parses their consolidated beneficiary/payment rows, and persists normalized passagens records in the local SQL database with idempotent reimport behavior.
- `public-passagens-agent-access`: Exposes imported `passagens` records through dedicated public tools and chatbot integration so the agent can answer lookup and aggregate questions about passagens from the local database.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/pipeline.py`, a new or extended CSV parser area under `ingestion/parsers/csv/`, `ingestion/schemas/despesas.py` and/or adjacent schemas, `database/models/expenses.py`, migrations under `database/migrations/versions/`, public SQL tools under `agents/tools/sql_tools/`, routing under `agents/routing/`, chatbot prompt/docs, and related tests.
- Affected systems: local CSV ingestion, SQL persistence for transparency data, public tool registration, agent routing, and chatbot answer generation.
- Affected behavior: supported `passagens` files become part of `uv run python cli.py importar`, imported rows become queryable from SQL, and `passagens` questions can be answered through dedicated tools instead of being unsupported.
- Risk areas: CSV header/encoding drift, overlap between `passagens` and generic `despesas` tool behavior, idempotent reimport rules for consolidated rows, and exposing only fields that truly exist in the source file.
