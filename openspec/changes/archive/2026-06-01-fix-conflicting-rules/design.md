## Context

The repository currently has overlapping rule systems that influence the same user-visible behavior:

- deterministic router and guardrail logic in `agents/router.py`,
- conversational policy in `docs/agent-system-prompt.md`,
- domain-local usage guidance in tool docstrings, schemas, and return hints,
- separate runtime entrypoints that do not enforce the same rule stack in the same order.

This causes three kinds of conflict:

1. The same query behavior is defined more than once, sometimes with different expectations.
2. Some rules are enforced in one entrypoint but treated as prompt-only guidance in another.
3. There is no explicit ownership model saying which layer is authoritative for safety, conversational interpretation, or tool-specific chaining guidance.

This change focuses on resolving those conflicts without requiring a full rewrite of the agent architecture. The goal is to make rule precedence and rule ownership explicit so future evolution does not recreate silent contradictions.

## Goals / Non-Goals

**Goals:**
- Establish a clear precedence order for agent rules.
- Ensure non-negotiable rules are enforced consistently across entrypoints.
- Clarify which layer owns hard safety, conversational interpretation, and tool-local behavior.
- Remove or rewrite conflicting duplicate rules so representative citizen queries behave consistently.
- Add regression coverage for rule-conflict scenarios that previously depended on implicit behavior.

**Non-Goals:**
- Rebuilding every agent path around a brand-new orchestration framework.
- Changing the public-data scope, SQLite model, or SQL tool inventory.
- Eliminating all router code immediately.
- Solving every possible UX problem in the prompt; this change is about consistency and precedence first.

## Decisions

### 1. Define a strict rule precedence hierarchy

The system will treat rule layers in this order:

1. Hard-coded pre-agent guardrails
2. Agent runtime contract and prompt-level conversational policy
3. Tool contracts, schemas, and tool-return hints
4. Compatibility routing helpers and legacy heuristics

Rationale:
- Safety and scope protections must not depend on model obedience.
- Prompt policy is the best place for cross-domain conversational interpretation.
- Tool-local guidance is authoritative for domain-specific follow-up behavior and parameter expectations.
- Compatibility routing is useful, but it cannot remain an equal peer to the layers that define product behavior.

Alternatives considered:
- Keep all layers as co-equal sources of truth: rejected because that is the current problem.
- Push everything into code: rejected because many interpretation rules are conversational and already live naturally in prompt/tool contracts.

### 2. Give each rule category a single owner

The implementation will classify existing rules by owner:

- Hard guardrails own scope rejection, empty-query handling, and prompt-injection refusal.
- Prompt/runtime policy owns clarification rules, memory/reference handling, and high-level tool orchestration.
- Tool contracts own domain-local follow-ups, ambiguity handling, and parameter constraints for specific queries.
- Router helpers own only compatibility behavior that does not contradict the first three layers.

Rationale:
- Conflicts happen when multiple layers define the same type of behavior.
- Ownership makes future changes easier to review and test.

Alternatives considered:
- Keep overlapping definitions but try to sync them manually: rejected because it does not scale and is error-prone.

### 3. Normalize entrypoints around the same hard-rule boundary

Any citizen-facing entrypoint that invokes the assistant must enforce the same hard pre-agent checks before model execution. Allowed queries may still use different runtime wrappers during migration, but they must not disagree on safety or scope outcomes.

Rationale:
- Rule conflicts are magnified when one path enforces code-level safeguards and another treats them as optional.
- Cross-entrypoint consistency is necessary even if compatibility adapters remain temporarily.

Alternatives considered:
- Fix only the chatbot path: rejected because contradictions would remain in other supported paths.

### 4. Treat router heuristics as subordinate compatibility logic

Router heuristics that currently encode conversational behavior will be audited and either:
- moved into prompt/tool contracts, or
- explicitly retained as compatibility helpers where they do not conflict with the authoritative layers.

Rationale:
- The router currently mixes hard invariants with interpretation policy.
- Making it subordinate prevents it from silently contradicting prompt/tool behavior.

Alternatives considered:
- Delete the router immediately: rejected because some helpers may still be useful during migration and regression testing.

### 5. Test conflict resolution as a first-class behavior

Regression coverage will focus on cases where rules previously overlapped or disagreed, such as:
- blocked versus allowed queries across entrypoints,
- salary/payment flows involving elected officials,
- acronym clarification before tool execution,
- contract and licitacao follow-up expectations.

Rationale:
- A precedence model is only real if conflicting cases are tested explicitly.
- These tests will guard against future prompt edits or tool updates reintroducing contradictions.

Alternatives considered:
- Continue relying mainly on route-match tests: rejected because they validate the compatibility layer, not the rule contract the user experiences.

## Risks / Trade-offs

- [Risk] Some useful router behavior may be removed before its prompt/tool replacement is fully equivalent. -> Mitigation: audit query families before demoting a heuristic and add targeted regression tests for migrated behaviors.
- [Risk] Prompt and tool guidance may still drift over time after the initial cleanup. -> Mitigation: document rule ownership and keep conflict-oriented tests close to the affected flows.
- [Risk] Different entrypoints may appear aligned while still using subtly different bootstrap defaults. -> Mitigation: include bootstrap and guardrail alignment in the implementation scope, not just text cleanup.
- [Risk] The cleanup may overlap with broader orchestrator work and create proposal duplication. -> Mitigation: keep this change focused on precedence, ownership, and consistency rather than full architecture replacement.

## Migration Plan

1. Inventory existing rules from router logic, prompt instructions, tool contracts, and runtime wrappers.
2. Classify each rule by owner and identify contradictions or duplicated definitions.
3. Align entrypoints on the same pre-agent guardrail boundary.
4. Rewrite or remove conflicting rule definitions so only the owning layer remains authoritative.
5. Add regression tests for representative conflict cases and update runtime/operator documentation.

Rollback strategy:
- Keep compatibility routing behavior available during migration, but make sure the old path still respects the unified hard-rule boundary if rollback is needed.

## Open Questions

- Which remaining non-chatbot entrypoints are still considered supported enough to require full consistency guarantees?
- Should model default/configuration conflicts be fixed inside this change or treated as adjacent cleanup once rule ownership is settled?
- Are there any router heuristics that should remain authoritative because they encode legal or policy constraints rather than conversational behavior?
