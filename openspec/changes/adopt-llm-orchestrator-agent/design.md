## Context

The repository currently exposes two different agent behaviors:

- `main.py` builds an agent behind deterministic routing, query guardrails, and per-query tool filtering.
- `agents/chatbot/agent.py` builds a broader agent that exposes all public tools directly and relies on the system prompt plus tool contracts to orchestrate behavior.

This split creates three problems:

1. User-facing behavior is defined in multiple places at once: router heuristics, system prompt instructions, and tool docstrings/results.
2. The chatbot path is more flexible and conversational, but it does not currently apply the same hard pre-agent protections as the router-driven path.
3. Architecture drift is already visible in configuration and defaults, which makes future behavior changes harder to reason about and test.

The proposed change intentionally treats the chatbot path as the product direction: the LLM becomes the primary orchestrator for public-data questions, while code keeps only a narrow set of hard invariants.

## Goals / Non-Goals

**Goals:**
- Make the chatbot runtime the canonical citizen-facing behavior.
- Enforce hard scope and safety guardrails before model invocation.
- Let the model orchestrate tool choice, multi-step chaining, and conversational follow-ups across domains.
- Reduce duplication between router rules, prompt instructions, and tool contracts.
- Preserve compatibility for existing entrypoints while clarifying which layer owns which behavior.

**Non-Goals:**
- Removing every routing helper or legacy adapter in one step.
- Rewriting all SQL tools or changing the underlying SQLite data model.
- Expanding the domain scope beyond public municipal transparency data.
- Replacing prompt and tool contract guidance with a fully code-driven workflow engine.

## Decisions

### 1. Keep hard pre-agent guardrails in code, not in the prompt alone

The chatbot entrypoint will apply a pre-agent validation step for empty queries, out-of-scope requests, and prompt-injection attempts before invoking the LLM.

Rationale:
- These are non-negotiable protections.
- They are simpler to test deterministically than prompt behavior.
- They close the current gap between the router-driven path and the chatbot path.

Alternatives considered:
- Prompt-only guardrails: rejected because it weakens enforcement and makes failures harder to diagnose.
- Full router retention: rejected because most router logic is interpretation policy, not safety policy.

### 2. Use the LLM as the primary runtime orchestrator for allowed queries

For queries that pass guardrails, the chatbot agent will receive the public toolset without deterministic per-query filtering and will be expected to decide:
- which tool to call,
- whether a follow-up question is required,
- when to chain multiple tools,
- when contextual references such as `dele`, `essa secretaria`, or prior results should drive the next step.

Rationale:
- This matches the current citizen-facing prompt and tool contract model.
- Cross-domain questions are easier to support when the model can reason over the whole request and conversation.
- It removes the need to keep central routing heuristics in sync with tool semantics.

Alternatives considered:
- Keep per-query tool filtering: rejected because it preserves the current split-brain architecture and makes conversational chaining brittle.
- Build a formal workflow graph for each question class: rejected as too rigid for the current product stage.

### 3. Move interpretation policy into prompt and tool contracts

Rules that infer list vs aggregate behavior, interpret "top N", detect when to ask for period, or decide which follow-up tool should run after an empty/zero-value result will be owned by:
- the system prompt,
- tool docstrings and parameter schemas,
- tool result affordances such as `aviso`, `sugestao`, `candidatos`, and metadata.

Rationale:
- These rules describe conversational intent, not infrastructure.
- The tools already contain a large share of this guidance.
- Keeping interpretation near the tool contract reduces duplication and makes capability-specific behavior easier to evolve.

Alternatives considered:
- Preserve central route modules as the source of truth: rejected because the source of truth is already split and difficult to maintain.

### 4. Recast the router as a thin safety and compatibility layer

The existing router module will no longer be treated as the primary brain for the chatbot runtime. Its future role should be limited to:
- reusable guardrail helpers,
- optional legacy/compatibility entrypoints,
- test fixtures or observability aids for known query patterns.

Rationale:
- The current router still contains useful deterministic safety logic.
- It also contains a large amount of policy that should stop driving runtime behavior.
- This preserves a migration path without anchoring the product to the old architecture.

Alternatives considered:
- Delete the router entirely: rejected because it would couple architectural cleanup to unnecessary code removal.

### 5. Align tests around behavior, not heuristic route matches

Coverage will shift toward:
- hard-guardrail tests,
- chatbot orchestration tests,
- tool contract tests for chained behaviors and ambiguity handling,
- end-to-end query tests for representative citizen questions.

Rationale:
- Route-match tests are brittle once routing is no longer the primary runtime mechanism.
- Behavior-focused tests better capture the product promise.

Alternatives considered:
- Keep route tests as the main regression suite: rejected because they would preserve the wrong abstraction boundary.

## Risks / Trade-offs

- [Risk] The model may choose an inefficient or less precise tool path for some queries. -> Mitigation: strengthen prompt guidance, tool docstrings, and representative orchestration tests.
- [Risk] Removing deterministic tool filtering could expose more failure modes during tool selection. -> Mitigation: retain narrow hard guardrails and add tool-level validation and response hints.
- [Risk] Prompt and tool contracts may drift apart over time. -> Mitigation: document contract ownership clearly and add regression tests for the main chained flows.
- [Risk] Legacy entrypoints may behave differently during migration. -> Mitigation: keep compatibility wrappers until the chatbot path is the explicit default and tested.
- [Risk] Some route heuristics may still encode useful edge-case behavior not yet captured elsewhere. -> Mitigation: audit route modules during implementation and translate only the necessary behavior into prompt/tool contracts before removing runtime dependence.

## Migration Plan

1. Extract or reuse guardrail enforcement so the chatbot path validates queries before model invocation.
2. Consolidate agent bootstrap so chatbot and legacy entrypoints share model configuration, prompt loading, and guardrail boundary semantics.
3. Update prompt and tool contracts for the main orchestration flows that were previously protected by router heuristics.
4. Reframe router usage as optional compatibility logic rather than primary decision-making for citizen chat.
5. Replace or downgrade route-centric tests with orchestration and guardrail behavior tests.

Rollback strategy:
- Keep the existing router-backed entrypoint available during migration so the system can temporarily fall back to deterministic routing if orchestrator regressions appear.

## Open Questions

- Should the compatibility path continue to call route-specific tool filtering for non-chatbot entrypoints, or should all entrypoints converge on the same broad-tool agent?
- Which query families still need deterministic pre-processing beyond scope and injection checks, if any?
- Should model defaults and agent bootstrap be fully unified as part of this change, or treated as a follow-on cleanup once orchestration ownership is settled?
