## ADDED Requirements

### Requirement: Deterministic policy gate runs before hybrid tool selection
The citizen-facing chatbot MUST apply a deterministic pre-selection policy gate before invoking hybrid tool selection. This gate MUST remain responsible for blocking empty queries, blocking prompt-injection attempts, admitting valid contextual follow-ups, and forcing clarification for protected ambiguity cases that cannot safely skip user confirmation.

#### Scenario: Blocked query never reaches the selector
- **WHEN** a user submits an empty query, a prompt-injection attempt, or an obviously out-of-scope request
- **THEN** the system returns the deterministic policy response without invoking hybrid tool selection
- **AND** the language model agent is not created for that request

#### Scenario: Protected acronym ambiguity is clarified before selection
- **WHEN** a user asks an otherwise in-scope question centered on an ambiguous acronym such as `UPA`, `UBS`, `PSF`, `CRAS`, or `CREAS` without prior session confirmation
- **THEN** the system asks one focused clarification question before hybrid tool selection runs
- **AND** it does not attempt candidate tool selection until the ambiguity is resolved

### Requirement: Hybrid selector returns candidate public tools for allowed queries
For a query that passes deterministic policy checks, the system MUST use a structured selector that evaluates the allowed query against the registered public-tool catalog and returns a bounded set of candidate tools for the subsequent agent invocation.

#### Scenario: Allowed query narrows the candidate tool set
- **WHEN** a user submits an allowed transparency question that clearly targets one or more supported public-data capabilities
- **THEN** the selector returns a structured `allow` decision with a bounded set of candidate public tools
- **AND** the subsequent agent invocation is restricted to that candidate tool set instead of the full public registry

#### Scenario: Cross-domain question can return multiple candidates
- **WHEN** a user submits an allowed question whose answer may require more than one domain
- **THEN** the selector may return multiple candidate public tools in the same decision
- **AND** it does not force the query into a single preselected domain path when more than one capability is plausibly relevant

### Requirement: Tool routability is owned by tool-local registration metadata
Public tools MUST expose routing metadata that is sufficient for hybrid selection to reason about representative usage without depending on a central domain keyword chain.

#### Scenario: Newly registered public tool becomes selectable through metadata
- **WHEN** a new public tool is registered with the required routing metadata contract
- **THEN** the hybrid selector can consider that tool for candidate selection without requiring a new router priority rule or domain token list entry

#### Scenario: Selector grounding uses tool-local examples and hints
- **WHEN** the selector evaluates an allowed query against the public-tool catalog
- **THEN** it uses the registered per-tool routing metadata as its grounding context
- **AND** routability does not depend on a hard-coded per-domain precedence chain in the main chatbot path

### Requirement: Hybrid selection does not precompute final tool arguments
The hybrid selector MUST narrow candidate tools without becoming a second deterministic orchestration engine. Final tool invocation arguments SHALL remain the responsibility of the downstream agent and tool contracts.

#### Scenario: Selector narrows tools while agent decides invocation details
- **WHEN** the selector returns an `allow` decision for an allowed query
- **THEN** the system passes only the selected candidate tools into the agent
- **AND** the agent remains responsible for deciding which candidate tool to call, in what order, and with which runtime arguments

### Requirement: Invalid or low-confidence selection falls back safely
If hybrid selection cannot produce a reliable structured decision for an otherwise allowed query, the system MUST fall back to a safe execution path rather than rejecting the query solely because candidate selection was uncertain.

#### Scenario: Low-confidence selection falls back to all public tools
- **WHEN** the selector returns a low-confidence `allow` decision for an otherwise allowed query
- **THEN** the system falls back to invoking the agent with the full public toolset
- **AND** it does not reject the query only because candidate narrowing was uncertain

#### Scenario: Invalid selector output falls back instead of failing closed
- **WHEN** the selector returns malformed structured output, unknown tool names, or an empty candidate list for an otherwise allowed query
- **THEN** the system falls back to the full public toolset for that query
- **AND** it does not expose a selector-internal failure as the final user-facing outcome
