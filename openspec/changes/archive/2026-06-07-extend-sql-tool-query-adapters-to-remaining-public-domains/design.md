## Context

The archived `consolidate-sql-tool-query-mechanics` change introduced shared lookup and aggregate query-shape modules under `agents/tools/sql_tools/shared/` and migrated `contratos`, `servidores`, `receitas`, and `planejamento` onto that contract. The remaining public lookup+aggregate domain pairs still duplicate the old flow in local query files, including repeated `ValidationError` fallback handling, metadata assembly, grouped-vs-total aggregate branching, pagination messages, and empty-result suggestions.

Those remaining domains are not identical. `despesas`, `despesas_por_funcao`, `diarias`, `passagens`, `patrimonios`, `quadro_pessoal`, and `transferencias_financeiras` are mostly collection-backed after loading rows, while `licitacoes` still has a statement-backed path plus a text-filter branch that materializes rows to preserve object matching semantics. `licitacoes` also adds a domain-specific top-level summary field, `valor_total_estimado`, and row-level advisory decoration when estimated values are zero. The design therefore needs to extend the shared contract where necessary without pushing those domain rules into generic SQL-tool modules.

## Goals / Non-Goals

**Goals:**
- Migrate the remaining public lookup+aggregate SQL-tool domains onto the shared lookup and aggregate query-shape mechanics.
- Keep each migrated domain focused on field mappings, metric mappings, source-loading hooks, serializer hooks, and domain wording instead of repeating response orchestration.
- Preserve user-visible response contracts for ordering, pagination, empty-result suggestions, grouped aggregates, and domain-specific messages.
- Add any small shared extension points needed to support domain-owned top-level lookup extras and post-projection row decoration.
- Expand regression coverage so both the shared query shapes and the newly migrated domains remain stable.

**Non-Goals:**
- Migrating `eleitos`, `frotas`, or `folha_pagamento` in the same change.
- Rewriting collection-backed domains into SQL-first execution or changing the persistence model behind them.
- Changing public tool names, filter names, or the overall response envelopes exposed by the affected tools.
- Moving domain-owned caveats, advisories, or mixed-record normalization rules into generic shared modules.

## Decisions

### 1. Migrate the remaining domains in execution-style cohorts

The migration should proceed in two cohorts:

- collection-backed or mixed-record domains: `despesas`, `despesas_por_funcao`, `diarias`, `passagens`, `patrimonios`, `quadro_pessoal`, and `transferencias_financeiras`
- statement-backed and detail-heavy domain: `licitacoes`

This keeps the first wave of implementation focused on domains that already match the current shared collection helpers closely, while leaving the main edge case for a deliberate second step once the common adapter surface is proven.

Rationale:
- Most remaining duplication lives in the collection-backed domains, so they offer quick consolidation wins.
- `licitacoes` is the best stress test for statement-backed execution plus domain-owned lookup extras.

Alternatives considered:
- Migrate all eight domains in one undifferentiated pass: rejected because it hides the only meaningful technical edge case in a large review.
- Split every domain into its own proposal: rejected because the shared contract change is cross-cutting and benefits from a single design.

### 2. Extend the shared lookup contract to accept domain-owned response supplements

The shared lookup layer should support small adapter-owned additions beyond the base `total` / `resultados` / `metadata` envelope. The design should add an explicit extension point for:

- top-level response supplements such as `valor_total_estimado`
- post-projection row decoration such as `licitacoes` warnings for estimated value zero
- optional composed messages that must appear alongside the generic pagination message

The shared layer remains responsible for the common lookup lifecycle, while the adapter remains responsible for calculating and supplying these domain extras.

Rationale:
- `licitacoes` cannot adopt the current shared lookup builder cleanly without keeping part of the response shaping local.
- An explicit supplement hook preserves the shared contract without special-casing one domain inside generic code.

Alternatives considered:
- Leave `licitacoes` on its old implementation forever: rejected because it preserves avoidable duplication in the one remaining statement-backed public pair.
- Hardcode `valor_total_estimado` or advisory fields into the shared lookup module: rejected because those are domain-specific concerns, not subsystem defaults.

### 3. Keep aggregate sharing narrow and reuse the current contract whenever possible

The existing shared aggregate helpers already model the main branches the remaining domains need:

- total-only aggregate responses via `valor_total`
- grouped aggregate responses via `total_grupos` and paginated `resultados`
- statement-backed grouped execution and collection-backed grouped execution

This change should reuse that contract for the remaining domains and only add shared surface area if a concrete adopter exposes a missing branch during migration.

Rationale:
- The aggregate contract is already more complete than the lookup contract for this wave.
- Minimizing new generic surface area reduces the risk of overfitting the subsystem to one outlier.

Alternatives considered:
- Redesign the aggregate abstraction before migrating new adopters: rejected because the existing contract already fits the known domain shapes.

### 4. Keep domain-specific wording, fallbacks, and mixed-source normalization local

The adopting domains should own anything that encodes domain semantics rather than query-shape mechanics, including:

- `despesas` caveats about event-cost interpretation
- `licitacoes` empty-result guidance, object search semantics, detail toggles, and advisory row decoration
- `transferencias_financeiras` normalization across movement and emenda records
- any domain-specific default field sets, serializer details, or text-matching rules

The shared query-shape modules should call these behaviors through explicit hooks or adapter-supplied functions instead of absorbing them directly.

Rationale:
- The prior consolidation already established that shared ownership ends at orchestration, not at business wording.
- Mixed-source and advisory behavior are easier to verify when they stay local and explicit.

Alternatives considered:
- Push all custom messages into generic fallback strings: rejected because it would flatten citizen-facing guidance that depends on the domain meaning.

### 5. Expand tests at both the shared-shape and domain levels

The regression plan should add coverage for:

- shared lookup behavior with adapter-owned top-level extras and row decoration
- shared collection-backed adoption using at least one newly migrated domain
- shared statement-backed adoption using `licitacoes`
- public-tool regressions for each migrated domain family, especially pagination, ordering, empty-result suggestions, and grouped-total semantics

Rationale:
- The shared builders become a higher-leverage dependency after this wave than after the first consolidation.
- `licitacoes` introduces a new shared-contract edge case that deserves direct tests, not only end-to-end public tests.

Alternatives considered:
- Rely only on public-domain tests: rejected because the new shared lookup extension points need direct coverage.
- Rely only on shared tests: rejected because citizen-facing domain messages and summaries still need end-to-end protection.

## Risks / Trade-offs

- [Risk] The lookup builder may become too generic once response supplements are introduced. -> Mitigation: keep the extension point narrow, adapter-owned, and limited to explicit response and row-supplement hooks already required by current domains.
- [Risk] `licitacoes` object filtering may still need a partial custom path even after adopting the shared builder. -> Mitigation: design the contract around normalized execution results rather than forcing every domain through the same source-loading primitive.
- [Risk] Ordering or pagination messages may drift subtly during migration, especially in domains that currently sort collections with custom tie-break behavior. -> Mitigation: lock current ordering and pagination semantics in shared tests and domain tests before removing local orchestration.
- [Risk] Migrating eight domains in one proposal may produce a large implementation diff. -> Mitigation: implement by cohort, land the collection-backed adopters first, and migrate `licitacoes` only after the shared supplement hook is proven.

## Migration Plan

1. Inventory the duplicated lookup and aggregate steps across the eight target domains and separate shared orchestration from domain-owned hooks.
2. Add the minimal shared lookup extension points required for adapter-owned top-level response supplements and row decoration.
3. Migrate the collection-backed domains to the shared lookup and aggregate builders, removing thin local wrappers that no longer add domain behavior.
4. Migrate `licitacoes` onto the shared query-shape contract while preserving `valor_total_estimado`, detail toggles, object-search semantics, and advisory decoration locally.
5. Expand shared query-shape tests and update public-tool regressions for the migrated domains.
6. Remove obsolete duplicated query helpers and confirm the final domain adapters remain small and reviewable.

Rollback strategy:
- Revert the shared-adoption changes domain by domain while preserving the public tool entrypoints and schemas. Because the public response contracts stay stable, rollback can restore prior local orchestration without caller-facing changes.

## Open Questions

- Should the shared lookup supplement hook be expressed as a generic response-updates mapping, or as a narrower callback that returns validated response-only fields?
- After this wave, is it worth applying the lookup-only half of the contract to `eleitos` and `frotas`, or should those stay outside the shared query-shape family until they gain aggregate counterparts?
