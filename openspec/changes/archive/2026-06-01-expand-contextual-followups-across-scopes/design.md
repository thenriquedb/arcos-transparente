## Context

The current citizen-facing chatbot already preserves some conversational context at the model/tool layer, but the hard pre-agent guardrail boundary still decides scope admission mostly from the current turn plus a few narrow follow-up patterns. That makes concise refinements work in isolated cases while still rejecting natural continuations in other municipal-data domains when the user omits repeated subject, period, or filter terms.

This change is cross-cutting because the same pre-model decision is shared by the chatbot core and compatibility guardrail wrapper, while the actual follow-up execution remains owned by the LLM orchestration and tool contracts. The design therefore needs a shared admission model that is strict enough to keep out unrelated ellipses but broad enough to support natural contextual refinements across all supported public-data scopes.

## Goals / Non-Goals

**Goals:**
- Admit concise contextual follow-ups when a recent allowed public-data turn provides a trustworthy anchor.
- Make contextual follow-up admission consistent across supported citizen-facing entrypoints.
- Keep hard guardrail ownership centralized while allowing the LLM/tool layer to handle the actual domain execution after admission.
- Prevent blocked, empty, or out-of-scope turns from becoming context anchors.
- Add a repeatable regression matrix for representative follow-up patterns across multiple scopes.

**Non-Goals:**
- Building a full conversation-state engine or storing complete semantic parses for every turn.
- Replacing tool-level ambiguity handling with deterministic pre-agent execution logic.
- Guaranteeing that every possible elliptical follow-up can be resolved without clarification.
- Changing the supported municipal-data scope itself.

## Decisions

### Decision: Introduce shared public context anchors for guardrail admission

The guardrail layer will evaluate short follow-ups against a shared notion of a recent allowed public-data anchor rather than treating every turn as a fully standalone query. An anchor is established only by prior turns that were already allowed within the supported public-data scope.

Why:
- The regression happens before model execution, so the fix must live at the same boundary that currently blocks the query.
- Reusing a shared anchor model preserves one hard-rule owner for scope admission instead of duplicating ad hoc fixes per tool or entrypoint.

Alternatives considered:
- Let the LLM infer all follow-ups after guardrails: rejected because the guardrail would still block many valid follow-ups before the model can help.
- Add follow-up heuristics independently inside each tool: rejected because it fragments ownership and would not fix pre-agent scope rejection.

### Decision: Use a hybrid of generic follow-up shapes and domain-aware anchor validation

Admission will not rely on history alone. The system will combine generic contextual forms such as pronouns, year-only refinements, and short comparative continuations with validation that the recent anchor belongs to a supported municipal-data domain and carries enough reusable context for that follow-up family.

Why:
- A purely generic `has_history` rule is too permissive and risks admitting unrelated ellipses.
- A purely domain-specific ruleset without shared shapes would duplicate similar behavior across many scopes.

Alternatives considered:
- Broadly allow any short question when history exists: rejected because out-of-scope conversations could slip through.
- Depend only on keyword matches in the new turn: rejected because the regression comes from natural follow-ups that intentionally omit repeated keywords.

### Decision: Keep execution ownership below the guardrail boundary

Once a contextual follow-up is admitted, the LLM orchestration layer and tool contracts remain responsible for choosing tools, reusing filters, and asking clarifying questions when the reused context is still insufficient for reliable execution.

Why:
- The guardrail layer should decide admission, not perform full conversational reasoning for every domain.
- This preserves the existing architectural direction where the chatbot is the primary orchestrator for allowed public-data questions.

Alternatives considered:
- Deterministically rewrite every follow-up into a complete query before tool execution: rejected because it would recreate router-style interpretation drift in the hard-rule layer.
- Keep refusing ambiguous follow-ups at the guardrail layer: rejected because the user-visible problem is over-blocking normal in-scope continuations.

### Decision: Prefer recent qualifying anchors and stop across unrelated turns

Anchor lookup will prefer the most recent qualifying public-data turn and will not skip across intervening blocked or unrelated turns to recover an older anchor implicitly.

Why:
- This reduces the chance of reviving stale context after the conversation has changed topics.
- It produces predictable behavior for both users and tests.

Alternatives considered:
- Scan arbitrarily far back for any public turn: rejected because it can reconnect a vague follow-up to stale context unexpectedly.

## Risks / Trade-offs

- [Risk] Over-admitting vague ellipses that only coincidentally resemble a follow-up. -> Mitigation: require a recent allowed public anchor plus a recognized contextual follow-up pattern before bypassing the out-of-scope guardrail.
- [Risk] Reusing the wrong anchor after a topic switch. -> Mitigation: prefer the most recent qualifying anchor and stop when an intervening turn breaks the public-context chain.
- [Risk] Different scopes may need different minimum context fields. -> Mitigation: keep generic admission shared, but allow domain-aware validators to decide whether a given follow-up family is safe for that scope.
- [Risk] The compatibility wrapper could drift from the chatbot path again. -> Mitigation: route both paths through the same guardrail evaluator and keep explicit regression coverage for both.

## Migration Plan

1. Add spec-level contracts for cross-scope contextual follow-up admission and cross-entrypoint consistency.
2. Introduce or extend shared guardrail helpers for anchor extraction and follow-up admission.
3. Thread recent allowed user-query context through chatbot and compatibility entrypoints.
4. Expand regression coverage with representative follow-up cases across multiple public-data domains.
5. Roll out without API changes; rollback is a code-only revert of the new admission path if over-admission is detected.

## Open Questions

- Should the implementation persist explicit structured anchor metadata per turn, or derive anchors from recent user queries on demand as long as the same behavior is test-covered?
- Which minimum representative scope matrix should be required in tests for this change: one scenario per domain family, or a smaller matrix covering each follow-up pattern family?
