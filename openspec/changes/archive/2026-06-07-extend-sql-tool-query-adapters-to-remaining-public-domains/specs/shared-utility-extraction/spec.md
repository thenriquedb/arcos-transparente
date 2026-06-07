## MODIFIED Requirements

### Requirement: Repeated SQL-tool query orchestration is extracted into subsystem-shared modules
The system MUST extract materially repeated lookup and aggregate orchestration used by multiple SQL-tool domains into shared modules owned by the SQL-tool subsystem, rather than keeping near-identical execution flows in each domain package. This requirement MUST apply to the remaining public lookup+aggregate domain pairs as they are migrated onto the shared query-shape contract.

#### Scenario: Remaining repeated lookup flow is replaced by shared subsystem module
- **WHEN** a remaining public SQL-tool domain such as `despesas`, `despesas_por_funcao`, `diarias`, `licitacoes`, `passagens`, `patrimonios`, `quadro_pessoal`, or `transferencias_financeiras` repeats lookup steps such as validation fallback handling, ordering, pagination, projection, metadata assembly, or empty-result handling
- **THEN** that orchestration is extracted into `agents/tools/sql_tools/shared/` or another SQL-tool-owned shared area
- **AND** the adopting domain imports the shared flow instead of keeping a local copy of the same lifecycle

#### Scenario: Remaining repeated aggregate flow is replaced by shared subsystem module
- **WHEN** a remaining public SQL-tool domain repeats aggregate steps such as grouped-vs-total branching, group counting, metric ordering, `valor_total` handling, or grouped result shaping
- **THEN** that orchestration is extracted into an SQL-tool-owned shared module
- **AND** the adopting domain keeps only the mappings, loaders, and hooks needed to specialize the shared flow

### Requirement: Query extraction preserves the boundary between generic orchestration and domain rules
The extraction of SQL-tool query mechanics MUST keep domain-owned search semantics, fallback strategies, special serializer logic, and domain-specific lookup supplements outside the generic shared modules even when the surrounding orchestration becomes shared.

#### Scenario: Domain-owned lookup supplements are not promoted to global helpers
- **WHEN** a domain-specific lookup response needs extra summary fields, advisory row decoration, or citizen-facing wording that exists only because of that domain's data contract
- **THEN** that behavior remains in the owning domain package or adapter hook
- **AND** the generic SQL-tool shared modules expose extension points instead of hardcoding the domain rule

#### Scenario: Thin wrappers are removed only when they add no domain behavior
- **WHEN** a per-domain query helper or schema base exists only as a pass-through to the shared SQL-tool implementation after the second migration wave
- **THEN** it may be removed or collapsed during extraction
- **AND** wrappers that still carry meaningful domain behavior remain in place
