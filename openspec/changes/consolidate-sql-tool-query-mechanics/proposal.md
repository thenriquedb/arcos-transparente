## Why

The public SQL tool domains for `contratos`, `servidores`, `receitas`, and `planejamento` repeat the same lookup and aggregate scaffolding across per-domain query files, filter helpers, and thin schema bases. That duplication is already causing drift between SQL-backed and Python-backed implementations in filtering, sorting, projection, pagination, and aggregation semantics, which makes the tools harder to evolve safely and increases the cost of adding or refactoring domains.

## What Changes

- Introduce shared lookup and aggregate query-shape modules for SQL tools so common execution mechanics live in a few deep modules instead of being reimplemented per domain.
- Refactor the `contratos`, `servidores`, `receitas`, and `planejamento` tool families so each domain supplies only its field mapping, metric mapping, source/filter hooks, and any special serialization or fallback adapters.
- Remove or collapse shallow per-domain schema base layers that only wrap `SqlToolBaseSchema` without adding meaningful behavior.
- Align response semantics across SQL-backed and Python-backed domains, including filtering behavior, ordering rules, projection handling, totals/group counts, empty-result suggestions, and pagination messages.
- Add regression coverage around the shared lookup/aggregate shapes and representative domain adapters so query behavior stops drifting as new domains are added.

## Capabilities

### New Capabilities
- `sql-tool-query-adapters`: Defines a shared lookup and aggregate execution contract for public SQL tools where domains plug in field mappings, metric mappings, data-loading/filter hooks, and serializer adapters while preserving consistent response semantics.

### Modified Capabilities
- `shared-utility-extraction`: Extends the extraction boundary from repeated pure helpers to repeated SQL tool query orchestration, while keeping domain-specific fallback rules and special business behavior local to the owning domain.

## Impact

- Affected code: `agents/tools/sql_tools/contratos/*`, `agents/tools/sql_tools/servidores/*`, `agents/tools/sql_tools/receitas/*`, `agents/tools/sql_tools/planejamento/*`, and `agents/tools/sql_tools/shared/*`.
- Affected behavior: internal execution strategy for public lookup/aggregate tools and the consistency of their public metadata, ordering, filtering, projection, and aggregation semantics.
- Affected tests: `tests/tools/sql_tools/test_contratos_public_tools.py`, `tests/tools/sql_tools/test_servidores_public_tools.py`, `tests/tools/sql_tools/test_receitas_public_tools.py`, `tests/tools/sql_tools/test_planejamento_public_tools.py`, plus new shared-query-shape regression coverage.
- Risk areas: over-generalizing domain-specific fallback behavior, changing user-visible ordering or filtering semantics during consolidation, and accidentally moving Python-backed domains onto the wrong execution path.
