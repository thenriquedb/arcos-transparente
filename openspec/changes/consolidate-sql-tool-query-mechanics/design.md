## Context

The current public SQL-tool domains split along two implementation styles:

- `servidores` and most of `contratos` build SQLAlchemy statements, count against subqueries, and serialize rows after SQL execution.
- `receitas` and `planejamento` load domain rows into Python collections, then reimplement filtering, sorting, grouping, projection, and metric calculation in memory.

Even though the public response contracts are very similar, each domain currently repeats the same orchestration steps in its own `consultar_*`, `agregar_*`, `shared/querying.py`, and thin schema-base files. That duplication is already visible in:

- repeated `ValidationError` fallback handling,
- repeated metadata assembly and pagination messages,
- repeated lookup projection helpers,
- repeated aggregate branches for grouped vs total-only queries,
- repeated sorting and group-count semantics,
- shallow wrappers like `ServidoresToolBaseSchema`, `ReceitasToolBaseSchema`, `PlanejamentoToolBaseSchema`, and `ContratosToolBaseSchema` that add little or no behavior on top of `SqlToolBaseSchema`.

At the same time, not everything is generic. `contratos` has domain-specific fallback search behavior and capability-availability messages, while `servidores` resolves a default `mes_de_referencia` before filtering. The design therefore needs to consolidate the common mechanics without flattening those domain-owned rules.

## Goals / Non-Goals

**Goals:**
- Consolidate repeated lookup and aggregate orchestration into shared SQL-tool modules with one consistent execution contract.
- Keep public response semantics aligned across SQL-backed and Python-backed domains for totals, ordering, pagination, projection, metadata, and empty-result handling.
- Reduce each domain to a small adapter surface centered on field mappings, metric mappings, source/filter hooks, and serializer/fallback hooks.
- Preserve backend-appropriate execution strategies instead of forcing every domain into a single SQL-only or Python-only path.
- Add regression coverage that exercises the shared query shapes directly and through representative domains.

**Non-Goals:**
- Rewriting all SQL tools in the repository in one pass; this change is scoped to `contratos`, `servidores`, `receitas`, and `planejamento`.
- Changing public tool names, parameter names, or response envelopes as part of the consolidation.
- Forcing Python-backed domains to migrate to pure SQL execution in the same change.
- Genericizing domain business rules such as `contratos` fallback heuristics or `servidores` month defaulting into universal defaults.

## Decisions

### 1. Introduce shared lookup and aggregate shape modules under `agents/tools/sql_tools/shared/`

The repeated mechanics will move into a small number of deep modules owned by the SQL-tool subsystem, likely one lookup-oriented module and one aggregate-oriented module, plus any small support types they need.

Each shape module will own the common lifecycle:

- parameter validation fallback handling,
- source execution/loading orchestration,
- consistent ordering and pagination behavior,
- grouped vs total-only aggregate branching,
- metadata assembly,
- empty-result suggestions and pagination messages,
- JSON-safe numeric/result shaping at the outer boundary.

Rationale:
- The duplication is orchestration-heavy, not just helper-function-heavy.
- Subsystem-local shared ownership matches the existing `shared-utility-extraction` rules better than promoting query mechanics into top-level `shared/`.

Alternatives considered:
- Keep extracting only tiny helpers: rejected because the main drift lives in the execution flows, not only in leaf helpers.
- Create another layer of per-domain base classes: rejected because that keeps the same shallow structure and hides behavior behind inheritance rather than making the shared flow explicit.

### 2. Use explicit domain adapters instead of inheritance-heavy domain frameworks

Each domain will plug into the shared lookup and aggregate flows through a small adapter contract. The adapter is expected to provide only what varies by domain, such as:

- allowed sort and group field mappings,
- metric mappings,
- source-loading or statement-building hooks,
- filter-application hooks,
- row or entity projection/serialization hooks,
- default metadata values,
- optional hooks for domain-specific fallback or pre-processing.

Rationale:
- The domain differences are mostly declarative mappings plus a few lifecycle hooks.
- Explicit adapters keep the boundary reviewable and make it clear what remains domain-owned.

Alternatives considered:
- A giant configurable object that tries to encode every branch generically: rejected because it becomes difficult to read and encourages accidental coupling between domains.
- A class hierarchy with override methods for every step: rejected because the repo’s current duplication is better served by composition than by inheritance.

### 3. Keep execution strategy pluggable behind the shared contract

The shared query shapes will not assume that every domain starts from the same backend primitive. Instead, the adapter boundary will allow at least two broad execution styles:

- statement-backed execution for domains like `servidores` and `contratos`,
- collection-backed or hybrid execution for domains like `receitas` and `planejamento`.

The shared layer should normalize the response semantics while the adapter remains responsible for how records or grouped values are sourced efficiently and correctly.

Rationale:
- The problem to solve is semantic drift, not forced backend uniformity.
- This preserves room for later SQL migrations without requiring them now.

Alternatives considered:
- Convert `receitas` and `planejamento` to SQL-first execution in the same change: rejected because it expands scope and mixes architectural cleanup with backend redesign.
- Preserve separate SQL-backed and Python-backed orchestration stacks forever: rejected because it institutionalizes the current drift.

### 4. Keep domain quirks local through explicit hooks

The shared modules will expose narrow extension points for domain-specific behavior that cannot be made generic without loss of clarity. Examples already visible in the codebase include:

- `servidores` deciding a default `mes_de_referencia` before running the rest of the query,
- `contratos` checking available columns/tables and producing domain-specific advisory messages,
- `contratos` text-fallback search behavior across semantically related fields.

These behaviors should remain in domain-owned adapters or local shared modules and be invoked explicitly by the shared flow only when the adapter declares them.

Rationale:
- The change should shrink domains to their real business differences, not erase them.
- Explicit hooks are easier to test than hidden conditional branches embedded in a generic core.

Alternatives considered:
- Push all domain quirks into the shared module behind feature flags: rejected because it turns the generic layer into a rule dump.
- Leave orchestration duplicated wherever a domain has one special case: rejected because most of each flow is still shared.

### 5. Collapse shallow wrapper bases only when they add no behavior

Per-domain schema bases that merely subclass `SqlToolBaseSchema` without adding validators, aliases, or serialization behavior should be removed or bypassed as part of the consolidation. If a wrapper still carries real domain behavior in the future, it can remain.

Rationale:
- Thin pass-through bases make the query layer look deeper than it is.
- Removing empty wrappers supports the broader goal of reducing shallow per-domain scaffolding.

Alternatives considered:
- Keep all wrapper bases for symmetry: rejected because symmetry alone does not justify extra indirection.
- Remove every local base unconditionally: rejected because some future domain may still need a meaningful local base contract.

### 6. Protect the consolidation with shape-level and adopter-level tests

The test plan should cover both:

- direct behavior of the shared lookup and aggregate flows,
- representative adopters from each backend style, such as one SQL-backed domain and one Python-backed or hybrid-backed domain for lookup and aggregate cases.

The assertions should emphasize query shape semantics:

- stable totals and group counts,
- preserved ordering and tie-break behavior,
- consistent projection behavior,
- preserved empty-result suggestions,
- unchanged domain-specific fallback/defaulting where applicable.

Rationale:
- Shared modules become high-leverage dependencies immediately.
- Domain tests alone may miss regressions in the shared execution contract, while shared-only tests may miss integration errors.

Alternatives considered:
- Rely only on existing domain tests: rejected because the new shared boundary deserves direct coverage.
- Replace domain tests with shared tests: rejected because public tool contracts still need representative end-to-end protection.

## Risks / Trade-offs

- [Risk] The adapter contract may become too abstract and harder to understand than the duplication it replaces. -> Mitigation: keep the first version narrow, centered on current repeated steps, and avoid anticipating unrelated future domains.
- [Risk] Public ordering or pagination semantics may change subtly during migration, especially where one domain uses SQL ordering and another uses Python sorting. -> Mitigation: preserve current tie-break behavior explicitly in tests before and after migration.
- [Risk] `contratos` availability checks and fallback heuristics may be accidentally flattened into generic logic. -> Mitigation: keep those paths behind domain-owned hooks and verify them with domain-specific regression tests.
- [Risk] The shared layer could accidentally coerce Python-backed domains into inefficient behavior or SQL-backed domains into premature materialization. -> Mitigation: keep source loading/execution strategy adapter-owned and review each adopter for backend-appropriate execution.
- [Risk] Refactoring four domains in one change may create a large review surface. -> Mitigation: migrate one representative SQL-backed domain and one representative Python-backed domain first, then apply the same shared contract to the remaining domains with the pattern already proven.

## Migration Plan

1. Inventory the repeated lookup and aggregate steps across `contratos`, `servidores`, `receitas`, and `planejamento`, separating generic orchestration from domain-owned rules.
2. Introduce shared SQL-tool query-shape modules and their adapter types under `agents/tools/sql_tools/shared/`.
3. Migrate one SQL-backed adopter and one Python-backed or hybrid-backed adopter to validate the adapter contract against both execution styles.
4. Migrate the remaining two domains, keeping domain-specific fallback/defaulting logic behind explicit hooks.
5. Remove or collapse thin schema/query wrappers that no longer add domain behavior.
6. Add or update shared-flow and representative domain regression tests, then run the focused SQL-tool public test suite.

Rollback strategy:
- Revert the shared module adoption domain by domain. Because the public tool entrypoints remain the same, rollback can restore the prior per-domain orchestration without requiring caller-facing contract changes.

## Open Questions

- Should the first shared implementation normalize ordering tie-breaks to a single cross-domain rule, or preserve each domain’s current secondary ordering exactly even when they differ?
- Is it cleaner to model statement-backed and collection-backed execution as two adapter subtypes up front, or to start with a single minimal protocol and split only if the shared code becomes noisy?
