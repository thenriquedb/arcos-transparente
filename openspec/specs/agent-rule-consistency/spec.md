# agent-rule-consistency Specification

## Purpose
TBD - created by archiving change fix-conflicting-rules. Update Purpose after archive.
## Requirements
### Requirement: Explicit rule precedence
The system MUST apply a documented precedence order when multiple rule layers could influence the same user-visible behavior. Hard-coded pre-agent guardrails MUST take precedence over prompt instructions, tool contracts, and compatibility routing logic.

#### Scenario: Guardrail precedence overrides lower layers
- **WHEN** a user request is empty, out of scope, or attempts prompt injection
- **THEN** the hard guardrail layer blocks or rejects the request before model execution
- **AND** no lower-priority prompt, tool, or router rule may override that outcome

#### Scenario: Lower layers handle allowed-query behavior
- **WHEN** a request passes hard guardrails
- **THEN** conversational interpretation and tool orchestration are handled by the authoritative lower layers defined for allowed queries
- **AND** compatibility routing does not supersede that precedence order

### Requirement: Single owner per rule category
Each rule category MUST have one authoritative owner so the same behavior is not defined inconsistently in multiple layers. At minimum, hard safety rules, conversational interpretation rules, and tool-local domain rules SHALL each have a distinct owner.

#### Scenario: Safety rule ownership is code-level
- **WHEN** a rule concerns scope enforcement, empty-query handling, or prompt-injection refusal
- **THEN** the system treats the hard-coded guardrail layer as the authoritative owner
- **AND** any duplicate prompt or router wording is subordinate to that owner

#### Scenario: Conversational interpretation ownership is not duplicated as authoritative router logic
- **WHEN** a rule concerns follow-up questions, ambiguity clarification, reference reuse, or high-level tool selection
- **THEN** the system treats the conversational orchestration layer as the authoritative owner
- **AND** compatibility routing, if present, does not define a contradictory authoritative behavior for the same case

#### Scenario: Domain-local follow-up ownership stays with the tool contract
- **WHEN** a rule concerns tool-specific ambiguity handling, parameter validation, or domain-local follow-up expectations
- **THEN** the relevant tool contract is treated as the authoritative owner for that domain behavior

### Requirement: Cross-entrypoint consistency for non-negotiable behavior
Supported citizen-facing entrypoints MUST produce the same non-negotiable outcome for the same query when the behavior is governed by hard rules or explicit rule ownership.

#### Scenario: Same blocked query yields same outcome across entrypoints
- **WHEN** the same blocked query is submitted through two supported citizen-facing entrypoints
- **THEN** both entrypoints reject it for the same governing reason category
- **AND** neither path invokes the language model for that request

#### Scenario: Same allowed-query rule family does not diverge by entrypoint
- **WHEN** the same in-scope query relies on a documented conversational or tool-owned rule
- **THEN** supported citizen-facing entrypoints honor the same rule ownership model
- **AND** they do not produce contradictory execution behavior solely because different wrappers were used

### Requirement: Conflicting duplicate rules are eliminated or reconciled
If the same behavior is currently described in more than one layer, the implementation MUST either remove the duplicate or reconcile the definitions so only one authoritative behavior remains.

#### Scenario: Duplicate rule definitions do not disagree at runtime
- **WHEN** a behavior has historically been described in router logic, prompt text, and tool guidance
- **THEN** the resulting system behavior follows one reconciled authoritative definition
- **AND** lower-priority duplicate wording does not create a contradictory runtime path

#### Scenario: Compatibility logic cannot silently reintroduce removed behavior
- **WHEN** a conflicting heuristic is demoted to compatibility-only status
- **THEN** the compatibility layer does not remain capable of overriding the authoritative owner for that behavior

### Requirement: Conflict-oriented regression coverage
The system MUST maintain regression coverage for representative cases where rule conflicts previously existed or could reasonably reappear after prompt, tool, or router changes.

#### Scenario: Regression coverage exists for representative conflict families
- **WHEN** the rule stack is updated
- **THEN** automated coverage verifies representative blocked-query, clarification, chaining, and ambiguity-resolution cases against the intended ownership model

#### Scenario: Rule-stack changes surface contract drift
- **WHEN** a prompt, tool contract, or compatibility heuristic changes a representative conflict case
- **THEN** regression coverage fails unless the updated behavior remains consistent with the documented precedence and ownership rules

