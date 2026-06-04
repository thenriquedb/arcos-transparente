# agent-rule-consistency Specification

## Purpose
TBD - created by archiving change fix-conflicting-rules. Update Purpose after archive.
## Requirements
### Requirement: Explicit rule precedence
The system MUST apply a documented precedence order when multiple rule layers could influence the same user-visible behavior. Hard-coded pre-agent guardrails and deterministic policy gates MUST take precedence over hybrid tool selection, prompt instructions, tool contracts, and compatibility routing logic.

#### Scenario: Guardrail precedence overrides lower layers
- **WHEN** a user request is empty, out of scope, or attempts prompt injection
- **THEN** the hard guardrail layer blocks or rejects the request before hybrid tool selection or model execution
- **AND** no lower-priority selector, prompt, tool, or compatibility router behavior may override that outcome

#### Scenario: Deterministic policy gate runs before allowed-query narrowing
- **WHEN** a request requires deterministic ambiguity handling or contextual admission before execution
- **THEN** the deterministic policy gate resolves that outcome before hybrid tool selection runs
- **AND** candidate tool narrowing does not bypass that policy boundary

#### Scenario: Lower layers handle allowed-query behavior after policy gates
- **WHEN** a request passes hard guardrails and deterministic policy checks
- **THEN** hybrid tool selection and conversational orchestration handle allowed-query execution
- **AND** compatibility routing does not supersede that precedence order

### Requirement: Single owner per rule category
Each rule category MUST have one authoritative owner so the same behavior is not defined inconsistently in multiple layers. At minimum, hard safety rules, deterministic clarification and continuity rules, hybrid tool selection, and tool-local domain rules SHALL each have a distinct owner.

#### Scenario: Safety rule ownership is code-level
- **WHEN** a rule concerns scope enforcement, empty-query handling, or prompt-injection refusal
- **THEN** the system treats the hard-coded guardrail layer as the authoritative owner
- **AND** any duplicate prompt, selector, or router wording is subordinate to that owner

#### Scenario: Clarification and continuity ownership stays in deterministic policy
- **WHEN** a rule concerns acronym confirmation, concise contextual follow-up admission, or post-clarification confirmation handling
- **THEN** the system treats the deterministic policy gate as the authoritative owner for that behavior
- **AND** neither hybrid tool selection nor compatibility routing may redefine that outcome authoritatively

#### Scenario: Allowed-query candidate narrowing belongs to hybrid selection
- **WHEN** a rule concerns which public tools are plausible candidates for an allowed citizen query
- **THEN** the system treats hybrid tool selection as the authoritative owner for candidate narrowing in the main chatbot path
- **AND** compatibility routing, if present, does not define a contradictory authoritative tool-selection path for the same query

#### Scenario: Domain-local execution ownership stays with the tool contract
- **WHEN** a rule concerns tool-specific ambiguity handling, parameter validation, fallback hints, or domain-local follow-up expectations
- **THEN** the relevant tool contract is treated as the authoritative owner for that domain behavior

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

### Requirement: Conflicting duplicate rules are eliminated or reconciled
If the same behavior is currently described in more than one layer, the implementation MUST either remove the duplicate or reconcile the definitions so only one authoritative behavior remains.

#### Scenario: Duplicate rule definitions do not disagree at runtime
- **WHEN** a behavior has historically been described in router logic, selector prompts, system prompt text, and tool guidance
- **THEN** the resulting system behavior follows one reconciled authoritative definition
- **AND** lower-priority duplicate wording does not create a contradictory runtime path

#### Scenario: Compatibility routing cannot silently reintroduce removed authority
- **WHEN** deterministic domain routing is demoted to compatibility-only status
- **THEN** the compatibility layer does not remain capable of overriding hybrid tool selection or deterministic policy ownership in the main chatbot runtime

### Requirement: Conflict-oriented regression coverage
The system MUST maintain regression coverage for representative cases where rule conflicts previously existed or could reasonably reappear after prompt, tool, or router changes.

#### Scenario: Regression coverage exists for representative conflict families
- **WHEN** the rule stack is updated
- **THEN** automated coverage verifies representative blocked-query, clarification, chaining, and ambiguity-resolution cases against the intended ownership model

#### Scenario: Rule-stack changes surface contract drift
- **WHEN** a prompt, tool contract, or compatibility heuristic changes a representative conflict case
- **THEN** regression coverage fails unless the updated behavior remains consistent with the documented precedence and ownership rules
