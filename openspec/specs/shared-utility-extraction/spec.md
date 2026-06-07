# shared-utility-extraction Specification

## Purpose
TBD - created by archiving change extract-common-shared-utilities. Update Purpose after archive.
## Requirements
### Requirement: Scope-based shared utility placement
The system SHALL organize extracted common methods and functions into separated shared folders based on ownership and reuse scope. Cross-cutting helpers used by multiple subsystems MUST live in top-level `shared/`, while helpers reused only inside one bounded subsystem MUST live in a local `shared/` area near that subsystem.

#### Scenario: Cross-cutting helper is placed in top-level shared
- **WHEN** a pure helper is reused by modules from more than one subsystem
- **THEN** the helper is extracted into a top-level `shared/` module
- **AND** consuming modules import it from that shared location instead of keeping local duplicates

#### Scenario: Bounded helper stays in subsystem-local shared folder
- **WHEN** a pure helper is reused only inside one bounded area such as ingestion schemas or SQL tool schemas
- **THEN** the helper is extracted into that subsystem's local `shared/` folder
- **AND** it is not promoted to top-level `shared/` unless cross-subsystem reuse is established

### Requirement: Repeated pure helpers are extracted and reused
Repeated pure helper logic SHALL be extracted from local modules into shared modules when the behavior is materially the same across more than one caller.

#### Scenario: Local duplicate helper is replaced by shared import
- **WHEN** two or more modules implement materially identical parsing, normalization, or metadata helper logic
- **THEN** one shared helper becomes the authoritative implementation
- **AND** the local duplicate implementations are removed or reduced to thin wrappers only when necessary for compatibility

#### Scenario: One-off helper remains local
- **WHEN** a helper is specific to one module's business behavior and has no meaningful second consumer
- **THEN** the helper remains local
- **AND** the extraction rules do not force artificial generalization

### Requirement: Behavior-preserving extraction
Extracting a common method or function into a shared folder MUST preserve the effective behavior expected by existing callers, including normalization results, validation semantics, and metadata structure.

#### Scenario: Extracted validation helper preserves accepted and rejected values
- **WHEN** a caller is migrated from a local helper to an extracted shared helper
- **THEN** representative valid inputs continue to normalize to the same effective values
- **AND** representative invalid inputs continue to fail in the same intended cases

#### Scenario: Extracted metadata helper preserves caller output shape
- **WHEN** a schema or filter module switches to a shared metadata serialization helper
- **THEN** the resulting metadata payload keeps the same structural contract expected by its callers and tests

### Requirement: Shared folders do not absorb domain business rules
The extraction process MUST not move domain-specific business behavior into generic shared modules merely because the code looks similar.

#### Scenario: Domain-specific rule stays with the owning context
- **WHEN** a helper encodes business semantics that are specific to one domain or workflow
- **THEN** that helper remains with the owning context or local shared folder
- **AND** only the truly generic sub-parts may be extracted

### Requirement: Regression coverage for extracted helper families
The system MUST maintain regression coverage for extracted shared helpers and for representative callers that adopt them.

#### Scenario: Shared helper has direct regression coverage
- **WHEN** a helper family is extracted into a shared module
- **THEN** automated coverage validates that helper's representative behavior directly

#### Scenario: Migrated callers remain behaviorally stable
- **WHEN** representative ingestion or SQL tool modules are updated to use extracted shared helpers
- **THEN** automated coverage verifies that the migrated callers still honor their expected parsing, normalization, and metadata behavior

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
