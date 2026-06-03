## Context

The repository currently maintains a deterministic router with per-domain keyword matching, extractors, and precedence ordering even though the citizen-facing chatbot already relies on a broader LLM orchestration model. This split leaves the system in an awkward middle state:

- hard safety and conversational continuity are mixed with domain-routing heuristics,
- adding or refining a domain often requires editing central token lists and route order,
- tests assert route payloads that no longer match the intended product boundary,
- public tool onboarding remains tightly coupled to router maintenance.

The desired direction is a precision-oriented hybrid model: deterministic code remains responsible for non-negotiable safety and clarification gates, while an LLM-backed selector narrows the candidate tool set for allowed queries without trying to precompute the full execution plan.

## Goals / Non-Goals

**Goals:**
- Remove deterministic per-domain route matching from the main chatbot execution path.
- Preserve deterministic handling for blocked queries, contextual continuity admission, and ambiguity cases that must not depend on model behavior alone.
- Introduce a structured pre-agent tool selector that returns candidate public tools, clarification requests, or a safe fallback.
- Make new public tools routable through tool-local metadata instead of central keyword-chain edits.
- Reframe tests around guardrail and selection behavior rather than exact route payload synthesis.

**Non-Goals:**
- Rewriting SQL tool contracts, schemas, or the SQLite data model.
- Replacing all prompt guidance with code-only workflows.
- Introducing vector search or an embedding dependency in the first version of selection.
- Preserving deterministic `tool_kwargs` synthesis for the main citizen-facing chat runtime.

## Decisions

### 1. Keep a deterministic policy layer ahead of any model-based selection

The runtime will preserve a code-level gate for:
- empty queries,
- prompt-injection attempts,
- obviously out-of-scope requests,
- concise contextual follow-ups already admitted by session history,
- acronym confirmation and post-clarification confirmations that must stay inside the public-data flow.

Rationale:
- These behaviors are safety or UX invariants, not domain interpretation.
- They are easy to regression-test deterministically.
- They prevent the selector from spending latency on requests that must be blocked or clarified anyway.

Alternatives considered:
- Prompt-only safety and clarification: rejected because it weakens enforcement and auditability.
- Keeping domain heuristics in the same layer: rejected because it preserves the current maintenance problem.

### 2. Replace route matching with a structured LLM selector that returns candidate tools, not final execution kwargs

For an allowed query, the new selector will receive:
- the normalized user question,
- a compact slice of recent session context,
- the catalog of public tools and their routing metadata.

It will return a structured decision with fields equivalent to:
- `action`: `allow`, `clarify`, or `block`,
- `candidate_tool_names`: a small bounded list of public tools,
- `confidence`: high, medium, or low,
- `clarification_question`: optional,
- `reason_code`: optional diagnostic.

The selector will NOT generate final `tool_kwargs` or replace the agent's reasoning loop. Instead, it reduces the tool surface area for the subsequent agent invocation.

Rationale:
- Candidate selection is far more stable than attempting to reconstruct the full execution plan with heuristics.
- This preserves cross-domain flexibility while keeping precision higher than exposing the full public registry every time.
- It avoids re-creating a second orchestration engine outside the agent.

Alternatives considered:
- LLM-first with all public tools always exposed: rejected because precision is the primary tradeoff and the public tool set will continue to grow.
- Heuristic route-to-kwargs mapping: rejected because it is the part that scales worst today.

### 3. Extend tool registration with routing metadata instead of central token ownership

Each public tool will expose selection-oriented metadata in the registry, such as:
- representative user-query examples,
- selection hints like lookup, aggregate, history, or retrieval,
- exclusions or neighboring-domain notes where relevant.

This metadata becomes the selector's main source of domain grounding. New tools become routable by updating the tool's own registration contract instead of editing a global route chain.

Rationale:
- Tool-local metadata scales better with domain growth.
- It keeps routing knowledge near the tool contract that already defines the tool's scope.
- It creates a clean future path to retrieval-based or embedding-assisted selection if needed later.

Alternatives considered:
- Keep global keyword constants and simply prune them: rejected because the ownership problem remains.
- Introduce embeddings immediately: rejected because the first version can reuse the existing model stack without new infrastructure.

### 4. Fallback to the full public toolset when selector confidence is low or output is invalid

If the selector returns low confidence, malformed structured output, unknown tool names, or an empty candidate set for an otherwise allowed request, the runtime will fall back to instantiating the agent with the full public toolset.

Rationale:
- A graceful fallback is safer than incorrectly hard-failing an allowed transparency question.
- It preserves the current chatbot flexibility as a backstop during migration.
- It lets the system evolve the selector without turning every selector miss into a user-facing outage.

Alternatives considered:
- Fail closed on invalid selector output: rejected because it would create brittle regressions for allowed queries.
- Retry the selector repeatedly: rejected because it adds latency and complexity before the fallback path is exhausted.

### 5. Retire the router from the main chatbot path and keep only compatibility-safe helpers

The main citizen-facing chat runtime will no longer depend on:
- `ROUTE_PRIORITY_CHAIN`,
- per-domain `_try_route_*` functions,
- deterministic route decisions that pre-select one domain and build `tool_kwargs`.

Any remaining router code should either:
- support deterministic guardrails and continuity helpers,
- serve legacy compatibility wrappers outside the main runtime,
- or be removed when no longer needed.

Rationale:
- The router's current role is broader than the architecture now wants.
- Maintaining both selector logic and route heuristics would recreate the same split-brain problem.
- This makes the codebase's ownership model easier to explain and test.

Alternatives considered:
- Keep the router facade and swap internals behind it: rejected because the user explicitly wants freedom to break from the existing abstraction.

## Risks / Trade-offs

- [Risk] The selector may omit a needed neighboring tool for a cross-domain question. -> Mitigation: allow multiple candidates, add representative examples, and fall back to the full public toolset on low confidence.
- [Risk] Tool metadata could drift or become uneven across domains. -> Mitigation: define a minimal metadata contract and add tests that ensure every public tool exposes the required routing fields.
- [Risk] Some useful router edge cases may be lost during cleanup. -> Mitigation: translate only the truly non-negotiable ones into deterministic policy or tool-local contracts before removing route dependencies.
- [Risk] The additional selector hop adds latency. -> Mitigation: keep selector prompts compact, avoid retries by default, and use a bounded candidate list.
- [Risk] Behavior-focused tests may miss subtle regressions previously caught by route assertions. -> Mitigation: convert the current route corpus into selection-evaluation fixtures that check candidate coverage and fallback behavior.

## Migration Plan

1. Introduce a new pre-agent selection module and decision schema without changing the current public-tool implementations.
2. Extend the public tool registry so tools can publish routing metadata needed by the selector.
3. Integrate the selector into the chatbot runtime after deterministic policy checks and before agent creation.
4. Convert route-centric tests into selector, guardrail, and chat-runtime behavior tests.
5. Remove router dependency from the main citizen-facing runtime and either delete or isolate remaining compatibility-only routing code.

Rollback strategy:
- Keep a temporary code path that can still build the chatbot with the full public toolset and no selector narrowing if selector regressions appear during implementation.

## Open Questions

- No open product questions remain for this proposal. Implementation may still decide exact field names for selector diagnostics as long as the structured behaviors in the specs are preserved.
