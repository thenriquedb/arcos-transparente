## 1. Shared Query-Shape Foundation

- [x] 1.1 Inventory the repeated lookup and aggregate steps across `contratos`, `servidores`, `receitas`, and `planejamento`, separating generic orchestration from domain-owned rules and hooks.
- [x] 1.2 Create shared lookup and aggregate query-shape modules plus any small adapter/support types under `agents/tools/sql_tools/shared/`.
- [x] 1.3 Define the adapter surface for sortable fields, group fields, metrics, source-loading/filter hooks, projection/serialization hooks, metadata defaults, and optional domain-specific extension points.

## 2. Domain Adapter Migration

- [x] 2.1 Migrate `servidores` lookup and aggregate tools to the shared query shapes while preserving `mes_de_referencia` default resolution and current response semantics.
- [x] 2.2 Migrate `receitas` lookup and aggregate tools to the shared query shapes while preserving the current collection-backed execution strategy and result semantics.
- [x] 2.3 Migrate `planejamento` lookup and aggregate tools to the shared query shapes while preserving the current hybrid SQL-plus-Python filtering behavior and result semantics.
- [x] 2.4 Migrate `contratos` lookup and aggregate tools to the shared query shapes while keeping fallback search behavior, availability checks, and advisory messages domain-owned.
- [x] 2.5 Remove or collapse thin per-domain schema/query wrappers that no longer add meaningful domain behavior after the shared migration.

## 3. Regression Coverage

- [x] 3.1 Add direct tests for the shared lookup query shape covering at least one SQL-backed adapter and one collection-backed or hybrid-backed adapter.
- [x] 3.2 Add direct tests for the shared aggregate query shape covering grouped execution, total-only execution, ordering, and empty-result behavior.
- [x] 3.3 Update representative public-tool tests for `servidores`, `receitas`, `planejamento`, and `contratos` to lock preserved ordering, projection, metadata, fallback/defaulting, and pagination semantics.

## 4. Verification And Cleanup

- [x] 4.1 Run the focused SQL-tool public test suites and fix any response-shape or semantic drift introduced by the consolidation.
- [x] 4.2 Remove obsolete duplicated query helpers left behind in domain-local modules and confirm the final adapters stay small and domain-focused.
