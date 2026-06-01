# public-contextual-followups Specification

## Purpose
TBD - created by archiving change expand-contextual-followups-across-scopes. Update Purpose after archive.
## Requirements
### Requirement: Concise follow-ups remain in scope when anchored to prior public context
The citizen-facing assistant MUST admit concise follow-up questions when the current turn can be anchored to a recent allowed municipal public-data query in the same session, even if the follow-up would appear incomplete when read in isolation.

#### Scenario: Year-only refinement after event-cost query
- **WHEN** the user asks `qual foi o custo do festival gastronomico de 2026?` and then asks `E o de 2025?`
- **THEN** the second turn remains inside the supported public-data scope
- **AND** the assistant may reuse the prior event/object context while changing only the requested year

#### Scenario: Domain follow-up reuses prior filters without full restatement
- **WHEN** the user asks `Quais contratos da saude?` and then asks `E em 2024?`
- **THEN** the second turn remains inside the supported public-data scope
- **AND** the assistant may reuse the prior domain and filter context instead of requiring the user to restate `contratos da saude`

#### Scenario: Same continuity contract applies outside contratos
- **WHEN** the user asks `Quanto foi arrecadado com IPTU em 2025?` and then asks `E em 2024?`
- **THEN** the second turn remains inside the supported public-data scope
- **AND** contextual follow-up admission does not depend on one domain-specific heuristic family only

### Requirement: Context anchors come only from prior allowed public turns
The system MUST inherit contextual follow-up anchors only from recent user turns that were already admitted as supported municipal public-data queries.

#### Scenario: Out-of-scope turn does not become a valid anchor
- **WHEN** the user asks an out-of-scope question such as `Como implementar uma lista encadeada em Python?` and then asks `E o de 2025?`
- **THEN** the second turn is not admitted solely because session history exists
- **AND** the assistant keeps the normal out-of-scope protection unless the user restates valid public-data context

#### Scenario: Intervening unrelated turn breaks the anchor chain
- **WHEN** the user first asks an allowed public-data question, then switches to a blocked or unrelated request, and later asks a short follow-up such as `E em 2025?`
- **THEN** the system does not silently reconnect that follow-up to the older public-data question
- **AND** it requires fresh usable context before treating the new turn as in scope

### Requirement: Ambiguous contextual follow-ups escalate inside the public-data flow
When a contextual follow-up is anchored to valid public-data context but still lacks enough information for reliable execution, the assistant MUST keep the request inside the public-data flow and ask a focused clarification instead of rejecting it as out of scope.

#### Scenario: Anchored follow-up asks for ranking without enough detail
- **WHEN** the user asks an allowed public-data question and then follows with a concise refinement such as `E as maiores?`
- **THEN** the assistant treats the new turn as an in-scope continuation of the prior public context
- **AND** it asks only for the missing detail needed to execute reliably if the reused context is still ambiguous
- **AND** it does not guess missing filters silently

