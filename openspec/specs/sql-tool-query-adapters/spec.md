# sql-tool-query-adapters Specification

## Purpose
TBD - created by archiving change consolidate-sql-tool-query-mechanics. Update Purpose after archive.
## Requirements
### Requirement: Shared lookup query shapes execute public SQL tool lookups consistently
The system MUST provide a shared lookup-query execution contract for public SQL tools so domains reuse the same mechanics for filtering, ordering, projection, pagination, metadata, and empty-result handling instead of reimplementing those steps per domain.

#### Scenario: Domain lookup adapter plugs into shared lookup flow
- **WHEN** a public SQL-tool domain provides the supported lookup adapter inputs such as source-loading hooks, sortable field mappings, projection behavior, and metadata defaults
- **THEN** the shared lookup flow executes the lookup and returns the supported response shape with `total`, `resultados`, `metadata`, and any applicable `mensagem` or `sugestao`

#### Scenario: Lookup semantics stay aligned across backend styles
- **WHEN** one domain is SQL-backed and another domain is Python-backed or hybrid-backed
- **THEN** both domains still honor the same lookup semantics for ordering, projection, pagination windows, and empty-result messaging while keeping their backend-specific loading strategy behind the adapter boundary

### Requirement: Shared aggregate query shapes execute totals and grouped aggregations consistently
The system MUST provide a shared aggregate-query execution contract for public SQL tools so totals, grouped aggregations, ordering, group counts, metadata, and empty-result behavior are implemented once and reused across domains.

#### Scenario: Grouped aggregation uses shared aggregate flow
- **WHEN** a public SQL-tool domain provides group-field mappings, metric mappings, serialization hooks, and aggregate source/filter hooks
- **THEN** the shared aggregate flow returns grouped results with the supported `total_grupos`, `resultados`, `metadata`, and optional pagination-style `mensagem`

#### Scenario: Total-only aggregation reuses the same contract
- **WHEN** `agrupar_por` is omitted for a supported public SQL-tool aggregate
- **THEN** the shared aggregate flow returns `valor_total` through the same domain adapter contract instead of requiring a separate per-domain orchestration path

### Requirement: Domain-specific query behavior remains adapter-owned
The system MUST keep domain-specific fallback behavior, domain-only defaulting rules, and special serialization adapters outside the generic shared query-shape modules even when the main lookup and aggregate mechanics are consolidated.

#### Scenario: Domain-specific fallback remains local
- **WHEN** a domain such as `contratos` needs fallback search behavior or capability-specific advisory messages
- **THEN** that behavior remains in the domain adapter or local shared module rather than being hardcoded into the generic shared lookup or aggregate flow

#### Scenario: Domain defaulting hook stays explicit
- **WHEN** a domain such as `servidores` needs a special defaulting rule like choosing a reference month before executing filters
- **THEN** the shared query flow calls that behavior through an explicit adapter hook instead of embedding the rule as a cross-domain default

### Requirement: Shared query-shape modules are protected by representative regression coverage
The system MUST maintain regression coverage for shared lookup and aggregate query shapes together with representative SQL-backed and Python-backed domain adopters.

#### Scenario: Shared lookup flow has representative coverage
- **WHEN** the shared lookup-query modules change
- **THEN** automated coverage verifies representative lookup behavior for at least one SQL-backed adopter and one Python-backed or hybrid-backed adopter

#### Scenario: Shared aggregate flow has representative coverage
- **WHEN** the shared aggregate-query modules change
- **THEN** automated coverage verifies representative grouped and total-only aggregate behavior for at least one SQL-backed adopter and one Python-backed or hybrid-backed adopter

