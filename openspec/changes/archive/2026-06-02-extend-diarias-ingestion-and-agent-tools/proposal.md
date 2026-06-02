## Why

The repository already recognizes `diárias` indirectly inside the broader `despesas` domain, but it does not yet define an explicit contract for loading dedicated `diarias` CSV files, persisting their travel-specific fields, and exposing them to the agent through first-class tools. We need that end-to-end flow so new `diarias` CSV deliveries become queryable data instead of depending on generic text matching over expense records.

## What Changes

- Extend ingestion so supported `diarias` CSV files are discovered, parsed, normalized, and loaded through the standard local import pipeline.
- Define how imported `diarias` records are stored in the SQL database, including travel-specific fields and safe re-import behavior.
- Add public `diarias` tools for list and aggregation queries, exposing travel-oriented filters and fields needed by the citizen-facing agent.
- Integrate the new `diarias` tools into router and prompt contracts so the agent can answer supported daily-travel questions directly from the local database.
- Add regression coverage for the full path from `diarias` file import to agent-visible tool usage.

## Capabilities

### New Capabilities
- `diarias-source-ingestion`: Discovers supported `diarias` CSV files, parses their travel and payment rows, and persists normalized daily-travel records in the local SQL database with idempotent reload behavior.
- `public-diarias-agent-access`: Exposes imported `diarias` records through dedicated public tools and chatbot integration contracts so the agent can answer lookup and aggregate questions about diárias from the local database.

### Modified Capabilities
- None.

## Impact

- Affected code: `ingestion/pipeline.py`, a new CSV ingestion/parser area for `diarias`, `ingestion/schemas/despesas.py` and/or new diarias schemas, `database/models/expenses.py`, migrations under `database/migrations/versions/`, new public tools under `agents/tools/sql_tools/`, routing files under `agents/routing/`, and prompt/docs files under `docs/`.
- Affected systems: local CSV ingestion workflow, SQL persistence for transparency data, public tool registration, query routing, and chatbot answer generation.
- Affected behavior: which `diarias` files are auto-discovered, what daily-travel attributes are stored, what list/aggregate questions can be answered directly, and how the agent chooses the correct tool path for `diárias`.
- Risk areas: dedicated `diarias` files diverging from the current `despesas` schema, weak deduplication across repeated imports, incomplete exposure of travel-specific fields in the public tool layer, and router/prompt drift from the new tool surface.
