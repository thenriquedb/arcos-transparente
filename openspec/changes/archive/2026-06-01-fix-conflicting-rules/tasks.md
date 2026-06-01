## 1. Rule Inventory

- [x] 1.1 Inventory the current rule definitions across router logic, chatbot/runtime wrappers, the system prompt, and tool contracts.
- [x] 1.2 Classify each inventoried rule by intended owner: hard guardrail, conversational orchestration, tool-local contract, or compatibility helper.
- [x] 1.3 Identify and document the concrete conflicts or duplicate definitions that currently affect runtime behavior.

## 2. Guardrail And Entrypoint Alignment

- [x] 2.1 Align supported citizen-facing entrypoints on the same hard pre-agent guardrail boundary for empty, out-of-scope, and prompt-injection queries.
- [x] 2.2 Normalize any bootstrap differences that would otherwise make two entrypoints enforce different non-negotiable outcomes.
- [x] 2.3 Add or update tests proving blocked queries behave consistently across supported entrypoints.

## 3. Rule Ownership Cleanup

- [x] 3.1 Remove or rewrite conflicting prompt, router, and tool-layer rules so each rule category has one authoritative owner.
- [x] 3.2 Demote conversational router heuristics that conflict with prompt/tool-owned behavior into compatibility-only helpers or remove them entirely.
- [x] 3.3 Update tool contracts and prompt wording where necessary so domain-local guidance and conversational policy no longer contradict each other.

## 4. Conflict Regression Coverage

- [x] 4.1 Add regression tests for representative rule-conflict families such as elected-official salary flows, acronym clarification, and contract-to-licitacao follow-ups.
- [x] 4.2 Replace or downgrade tests that assert router behavior as if it were still the primary runtime authority.
- [x] 4.3 Add checks ensuring compatibility logic cannot silently override the documented precedence model.

## 5. Documentation And Handoff

- [x] 5.1 Document the final rule precedence hierarchy and owner for each rule category in the relevant architecture or operator docs.
- [x] 5.2 Record any remaining compatibility-only router behavior and the conditions under which it is still allowed to exist.
