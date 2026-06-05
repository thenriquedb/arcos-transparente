## ADDED Requirements

### Requirement: Repeated SQL-tool query orchestration is extracted into subsystem-shared modules
The system MUST extract materially repeated lookup and aggregate orchestration used by multiple SQL-tool domains into shared modules owned by the SQL-tool subsystem, rather than keeping near-identical execution flows in each domain package.

#### Scenario: Repeated lookup flow is replaced by shared subsystem module
- **WHEN** two or more SQL-tool domains implement materially identical lookup steps such as ordering, pagination, projection, metadata assembly, or empty-result handling
- **THEN** that orchestration is extracted into `agents/tools/sql_tools/shared/` or another SQL-tool-owned shared area
- **AND** the adopting domains import the shared flow instead of keeping local copies

#### Scenario: Repeated aggregate flow is replaced by shared subsystem module
- **WHEN** two or more SQL-tool domains implement materially identical aggregate steps such as group counting, metric ordering, `valor_total` handling, or grouped result shaping
- **THEN** that orchestration is extracted into an SQL-tool-owned shared module
- **AND** the adopting domains keep only the domain-owned mappings and hooks needed to specialize the shared flow

### Requirement: Query extraction preserves the boundary between generic orchestration and domain rules
The extraction of SQL-tool query mechanics MUST keep domain-owned search semantics, fallback strategies, and special serializer logic outside the generic shared modules even when the surrounding orchestration becomes shared.

#### Scenario: Domain-owned quirks are not promoted to global query helpers
- **WHEN** a domain-specific behavior exists only because of one domain's data contract or business wording
- **THEN** that behavior remains in the owning domain package or its local shared module
- **AND** the generic SQL-tool shared modules expose hooks or adapter boundaries instead of absorbing the rule directly

#### Scenario: Thin wrappers are removed only when they add no domain behavior
- **WHEN** a per-domain query helper or schema base exists only as a pass-through to the shared SQL-tool implementation
- **THEN** it may be removed or collapsed during extraction
- **AND** wrappers that still carry meaningful domain behavior remain in place
