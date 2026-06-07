## Why

The first `consolidate-sql-tool-query-mechanics` change removed duplicated lookup and aggregate orchestration from `contratos`, `servidores`, `receitas`, and `planejamento`, but the same response-shaping and validation flow is still copied across the remaining public SQL-tool domain pairs. That leaves the repository with two parallel patterns for pagination, metadata, empty-result handling, `valor_total` and `total_grupos` semantics, which increases drift risk every time those tools evolve.

## What Changes

- Extend the shared SQL-tool lookup and aggregate query-shape mechanics to the remaining public lookup+aggregate domain pairs: `despesas`, `despesas_por_funcao`, `diarias`, `licitacoes`, `passagens`, `patrimonios`, `quadro_pessoal`, and `transferencias_financeiras`.
- Refactor those domains so they provide domain-owned adapters, mappings, loader hooks, and any custom messaging or serialization instead of reimplementing the common lookup and aggregate lifecycle locally.
- Remove or collapse per-domain schema bases and query helpers that only wrap the shared SQL-tool contract without adding meaningful domain behavior.
- Preserve domain-specific behavior such as `licitacoes` detail toggles and advisory messages, `despesas` event-cost caveats, and mixed-record handling in `transferencias_financeiras` behind explicit domain-owned hooks.
- Add regression coverage for the newly adopted domains and broaden shared-query-shape tests so future public SQL-tool domains follow one execution contract.
- Keep `eleitos`, `frotas`, and `folha_pagamento` out of scope for this pass because they do not yet fit the same lookup+aggregate pair shape.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sql-tool-query-adapters`: extend the shared lookup and aggregate adapter contract so the remaining public lookup+aggregate SQL-tool domains adopt the common execution flow while preserving domain-owned hooks.
- `shared-utility-extraction`: expand the set of SQL-tool orchestration now required to live in subsystem-shared modules instead of remaining duplicated in domain packages.

## Impact

- Affected code: `agents/tools/sql_tools/despesas/*`, `despesas_por_funcao/*`, `diarias/*`, `licitacoes/*`, `passagens/*`, `patrimonios/*`, `quadro_pessoal/*`, `transferencias_financeiras/*`, and `agents/tools/sql_tools/shared/*`.
- Affected behavior: internal execution strategy for public lookup and aggregate SQL tools, especially validation fallback handling, metadata assembly, grouped/total aggregate semantics, pagination messaging, and empty-result suggestions.
- Affected tests: `tests/tools/sql_tools/test_despesas_por_funcao_public_tools.py`, `test_diarias_public_tools.py`, `test_licitacoes_public_tools.py`, `test_passagens_public_tools.py`, `test_transferencias_financeiras_public_tools.py`, plus new or expanded shared query-shape coverage.
- Risk areas: flattening domain-specific messaging into the shared layer, changing existing ordering or grouped-result semantics while consolidating, and overfitting the shared contract to purely collection-backed domains before confirming it still fits `licitacoes`.
