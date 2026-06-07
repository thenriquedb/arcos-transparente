## 1. Shared Query-Shape Extension

- [x] 1.1 Inventory the duplicated lookup and aggregate flow across `despesas`, `despesas_por_funcao`, `diarias`, `licitacoes`, `passagens`, `patrimonios`, `quadro_pessoal`, and `transferencias_financeiras`, separating generic orchestration from domain-owned hooks and messages.
- [x] 1.2 Extend the shared lookup query-shape contract with the minimal adapter surface needed for domain-owned top-level response supplements and post-projection row decoration.
- [x] 1.3 Confirm the current shared aggregate helpers cover the remaining grouped and total-only branches, adding only the minimal shared serializer or hook support required by a concrete adopter.

## 2. Collection-Backed Domain Migration

- [x] 2.1 Migrate `despesas` and `despesas_por_funcao` lookup and aggregate tools to the shared query shapes while preserving their current filtering, ordering, and event-cost guidance semantics.
- [x] 2.2 Migrate `diarias` and `passagens` lookup and aggregate tools to the shared query shapes while preserving current period handling, sorting, pagination, and suggestion behavior.
- [x] 2.3 Migrate `patrimonios` and `quadro_pessoal` lookup and aggregate tools to the shared query shapes while preserving their current projection and grouping behavior.
- [x] 2.4 Migrate `transferencias_financeiras` lookup and aggregate tools to the shared query shapes while preserving mixed-record normalization across movimentacoes and emendas.
- [x] 2.5 Remove or collapse thin per-domain schema bases, query helpers, and response-shaping code that no longer add behavior after the collection-backed migrations.

## 3. Statement-Backed Domain Migration

- [x] 3.1 Migrate `consultar_licitacoes` to the shared lookup query shape while preserving `valor_total_estimado`, object-search semantics, detail toggles, and zero-value advisory decoration.
- [x] 3.2 Migrate `agregar_licitacoes` to the shared aggregate query shape while preserving both the statement-backed path and the object-search materialized path.
- [x] 3.3 Remove obsolete `licitacoes`-local orchestration that becomes redundant after the shared query-shape adoption.

## 4. Regression Coverage And Verification

- [x] 4.1 Expand `tests/tools/sql_tools/test_shared_query_shapes.py` to cover lookup supplements, row decoration, and representative collection-backed plus statement-backed adopters from the new migration wave.
- [x] 4.2 Update the affected public-tool regression suites to lock preserved ordering, pagination, empty-result suggestions, grouped totals, and domain-specific messages for each migrated domain family.
- [x] 4.3 Run the focused SQL-tool shared and public test suites, fix any semantic drift, and remove any obsolete helpers left behind by the consolidation.
