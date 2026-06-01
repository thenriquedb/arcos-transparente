## MODIFIED Requirements

### Requirement: Cross-entrypoint consistency for non-negotiable behavior
Supported citizen-facing entrypoints MUST produce the same non-negotiable outcome for the same query when the behavior is governed by hard rules or by documented contextual-admission rules that determine whether a follow-up remains inside the supported public-data scope.

#### Scenario: Same blocked query yields same outcome across entrypoints
- **WHEN** the same blocked query is submitted through two supported citizen-facing entrypoints
- **THEN** both entrypoints reject it for the same governing reason category
- **AND** neither path invokes the language model for that request

#### Scenario: Same documented contextual follow-up is admitted across entrypoints
- **WHEN** a short follow-up depends on a prior allowed public-data turn and is documented as an in-scope contextual continuation
- **THEN** supported citizen-facing entrypoints admit that follow-up into the allowed-query path
- **AND** none of them rejects it as out of scope solely because the current turn is terse or elliptical

#### Scenario: Same allowed-query rule family does not diverge by entrypoint
- **WHEN** the same in-scope query relies on a documented conversational or tool-owned rule
- **THEN** supported citizen-facing entrypoints honor the same rule ownership model
- **AND** they do not produce contradictory execution behavior solely because different wrappers were used
