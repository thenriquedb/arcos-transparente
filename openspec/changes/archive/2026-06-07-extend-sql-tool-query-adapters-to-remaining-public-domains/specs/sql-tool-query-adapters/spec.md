## MODIFIED Requirements

### Requirement: Shared lookup query shapes execute public SQL tool lookups consistently
The system MUST provide a shared lookup-query execution contract for public SQL tools so domains reuse the same mechanics for filtering, ordering, projection, pagination, metadata, and empty-result handling instead of reimplementing those steps per domain. The contract MUST also allow adapter-owned response supplements when a domain needs extra top-level lookup output that is not part of the base shared envelope.

#### Scenario: Domain lookup adapter plugs into shared lookup flow
- **WHEN** a public SQL-tool domain provides the supported lookup adapter inputs such as source-loading hooks, sortable field mappings, projection behavior, metadata defaults, and optional response supplement hooks
- **THEN** the shared lookup flow executes the lookup and returns the supported response shape with `total`, `resultados`, `metadata`, and any applicable `mensagem` or `sugestao`

#### Scenario: Domain-specific lookup extras stay compatible with the shared flow
- **WHEN** a domain such as `licitacoes` needs additional lookup output like `valor_total_estimado` or row-level advisory decoration after projection
- **THEN** the shared lookup contract preserves those domain-owned additions through explicit hooks without forcing the domain to reimplement pagination, ordering, projection, or empty-result handling

#### Scenario: Lookup semantics stay aligned across backend styles
- **WHEN** one domain is SQL-backed and another domain is Python-backed, mixed-record, or hybrid-backed
- **THEN** both domains still honor the same lookup semantics for ordering, projection, pagination windows, and empty-result messaging while keeping their backend-specific loading strategy and response supplement calculation behind the adapter boundary

### Requirement: Shared query-shape modules are protected by representative regression coverage
The system MUST maintain regression coverage for shared lookup and aggregate query shapes together with representative SQL-backed and Python-backed domain adopters. After the remaining public domain pairs adopt the shared contract, that coverage MUST continue to exercise both statement-backed and collection-backed adopters, including lookup responses that emit adapter-owned supplements.

#### Scenario: Shared lookup flow has representative coverage for adapter-owned supplements
- **WHEN** the shared lookup-query modules change
- **THEN** automated coverage verifies representative lookup behavior for at least one statement-backed adopter that emits domain-owned lookup extras and one collection-backed or mixed-record adopter that relies on the shared pagination and empty-result flow

#### Scenario: Shared aggregate flow has representative coverage after the second migration wave
- **WHEN** the shared aggregate-query modules change
- **THEN** automated coverage verifies representative grouped and total-only aggregate behavior for at least one statement-backed adopter and one collection-backed or mixed-record adopter from the expanded set of migrated public SQL-tool domains
