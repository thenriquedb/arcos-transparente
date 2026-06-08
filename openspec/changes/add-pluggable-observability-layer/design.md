## Context

The chatbot runtime already has clear orchestration boundaries in `agents/chatbot/core.py`, `agents/chatbot/policy.py`, `agents/chatbot/hybrid_selection.py`, `agents/chatbot/agent.py`, and the shared public-tool registry. Those seams are a good fit for observability because they capture the lifecycle of an allowed user query without forcing domain tools to know anything about a tracing provider.

Today the repository has no runtime-owned observability contract. There is no neutral interface for tracing request lifecycle, selection decisions, tool executions, or failures, and the current code would have to couple directly to a provider API if we integrated LangSmith ad hoc. The repository already documents OpenAI bootstrap settings in `.env.example`, and it even hints at LangSmith environment variables, but those variables are not part of a formal runtime contract yet.

This change is cross-cutting because it affects runtime bootstrap, chat orchestration, tool wrapping, configuration, and operator documentation at once. It also introduces an external dependency and a future-migration concern, so writing down the architectural boundary up front reduces the risk of provider-specific leakage.

## Goals / Non-Goals

**Goals:**
- Introduce a provider-neutral observability interface owned by the application runtime rather than by LangSmith.
- Make observability optional, with a no-op default when no provider is enabled.
- Capture the main execution stages of a user query: request entry, deterministic policy outcome, candidate-tool selection, agent invocation, tool execution, final response, and surfaced errors.
- Isolate LangSmith-specific bootstrap, credentials, and payload mapping inside one adapter module so a future Langfuse adapter can reuse the same interface.
- Extend the documented environment contract so operators can explicitly enable or disable tracing and supply provider-specific settings without changing application code.

**Non-Goals:**
- Supporting multiple observability backends in the first implementation beyond `none` and `langsmith`.
- Replacing LangChain or LangGraph's internal execution model.
- Instrumenting every helper function or every SQL query at the lowest level.
- Designing a generic organization-wide telemetry framework for unrelated services in the repository.

## Decisions

### 1. Introduce a runtime-owned observability facade with `noop` and provider adapters

Chosen direction:
- Add a small observability package, preferably under `agents/chatbot/observability/` or an equivalently local runtime boundary.
- Define a provider-neutral interface such as `ObservabilityProvider` plus lightweight run/span handles or context-manager helpers for nested runtime events.
- Ship a `NoOpObservabilityProvider` as the default implementation and a `LangSmithObservabilityProvider` as the first concrete adapter.
- Construct the active provider through a factory that receives validated observability config and returns the chosen adapter.

Why:
- The runtime needs one stable contract that the rest of the chatbot can depend on without importing LangSmith directly.
- A `noop` provider preserves current behavior for local development, tests, and deployments that do not want external tracing.
- A future Langfuse adapter should only require a new implementation and factory registration, not edits across the runtime.

Alternatives considered:
- Call LangSmith APIs directly from `agents/chatbot/core.py` and `agent.py`: rejected because it couples the chat lifecycle to one provider and makes migration noisy.
- Rely only on provider environment variables and implicit LangChain tracing: rejected because the repository would still lack an application-owned observability boundary and consistent hooks for selector/policy events outside the agent runtime.

### 2. Instrument stable runtime seams instead of domain modules

Chosen direction:
- Emit observability events around the following boundaries:
  - top-level chat request start/end in `ChatbotApplication.ask()` and `.stream()`
  - deterministic policy result before selection
  - hybrid selection decision, including fallback reason codes
  - backend agent invocation and streaming fallback behavior
  - public-tool execution lifecycle through the registry or equivalent tool-wrapping seam
  - surfaced exceptions and friendly error paths
- Keep domain tool implementations unchanged except for generic wrapping or shared helper integration.

Why:
- These seams already define the request lifecycle and match the mental model operators need when debugging the system.
- Wrapping at the registry/runtime level avoids scattering provider calls through every SQL or RAG tool.
- The contract remains focused on user-query orchestration rather than low-level internal noise.

Alternatives considered:
- Add tracing inside each public tool manually: rejected because it is repetitive, easy to forget, and ties domain code to observability concerns.
- Instrument only the LangChain agent call and nothing around it: rejected because policy decisions, hybrid selection, and fallback behavior would remain invisible even though they are some of the most important debugging surfaces in this project.

### 3. Keep provider-specific configuration separate from LLM bootstrap settings

Chosen direction:
- Extend the runtime configuration contract with observability-specific variables, separate from `LLM_PROVIDER`, `OPENAI_MODEL`, and `OPENAI_API_KEY`.
- Use canonical runtime-owned flags for enablement and provider selection, for example:
  - `OBSERVABILITY_ENABLED`
  - `OBSERVABILITY_PROVIDER`
- Accept provider-specific variables only inside the adapter/config validation path, such as:
  - `LANGSMITH_API_KEY`
  - `LANGSMITH_PROJECT`
  - `LANGSMITH_ENDPOINT`
- When observability is disabled or provider is unset, the runtime MUST use the no-op provider.
- When observability is explicitly enabled for `langsmith` but required provider settings are missing, bootstrap MUST fail fast with a clear configuration error.

Why:
- LLM runtime config and observability config solve different operational problems and should not share one overloaded contract.
- Explicit enablement prevents accidental outbound tracing from local environments.
- Fail-fast behavior is clearer than silently disabling tracing when operators explicitly asked for it.

Alternatives considered:
- Treat raw `LANGSMITH_*` variables as the only contract: rejected because it would leak provider vocabulary into the general runtime contract and make future provider additions awkward.
- Silently fall back to no-op when LangSmith is misconfigured: rejected because it hides operational mistakes after observability has been explicitly requested.

### 4. Use an allowlisted event payload model

Chosen direction:
- Define a narrow, runtime-owned event schema for what can be emitted: request id, session id, provider name, selected tool names, policy category, selector reason code, tool name, high-level status, and sanitized error details.
- Permit query text and model-facing question text where needed for debugging, but do not serialize environment secrets, raw credentials, or arbitrary internal objects.
- Keep provider adapters responsible for mapping this sanitized event model into provider-native metadata/tags.

Why:
- External observability backends can become accidental data sinks if the runtime forwards arbitrary objects.
- An allowlist makes migration easier because provider adapters translate from one internal model instead of reading ad hoc Python objects.
- It lowers the chance of secret leakage through tracing payloads.

Alternatives considered:
- Dump arbitrary metadata dicts from each layer into the provider: rejected because the payload would drift, become noisy, and risk leaking internal state.
- Capture only boolean success/failure without context: rejected because it would not be useful for debugging tool routing, policy decisions, or fallback behavior.

### 5. Wrap public tools at the registry seam

Chosen direction:
- Introduce observability-aware tool wrapping where tools are converted or exposed from `agents/tools/registry.py`.
- The wrapper should emit before/after/error events using the active provider while preserving the existing LangChain tool contract and tags.
- Wrapping must be generic so newly registered public tools become observable without domain-specific edits.

Why:
- The registry is the one place where public Python functions become runtime tools.
- This keeps observability orthogonal to tool business logic and aligned with the repository's tool metadata architecture.

Alternatives considered:
- Patch LangChain tool internals after agent creation: rejected because it is more brittle and harder to reason about than wrapping at the repository-owned seam.
- Leave tool execution entirely to provider auto-instrumentation: rejected because the project would lose control over naming, payload shape, and portability.

## Risks / Trade-offs

- [Observability adds external-runtime complexity] → Keep the default provider as no-op, validate config early, and document the opt-in path clearly.
- [Provider-neutral abstraction may under-model some LangSmith features] → Design around the common lifecycle the repository actually needs now, and allow provider adapters to enrich metadata internally without widening the shared contract prematurely.
- [Tracing user questions to an external service may raise data-handling concerns] → Use an allowlisted payload model, avoid secrets, and make observability explicitly opt-in through environment configuration.
- [Registry wrapping could subtly change tool behavior if implemented carelessly] → Preserve existing tool signatures/tags and cover wrapped tool execution with focused tests.
- [Future Langfuse support may need slightly different concepts than LangSmith] → Keep the shared contract centered on request, stage, tool, and error lifecycle instead of provider-native terminology like runs, traces, or spans.

## Migration Plan

1. Add the observability config model, provider factory, and no-op implementation without changing runtime behavior by default.
2. Add the LangSmith adapter and wire provider selection into chatbot bootstrap/runtime construction.
3. Instrument the chat lifecycle seams and registry-owned tool wrapping using the shared observability facade.
4. Extend `.env.example`, README, and architecture docs with the canonical observability contract and opt-in behavior.
5. Add focused tests for disabled mode, enabled-but-misconfigured mode, and LangSmith adapter wiring through the runtime seams.

Rollback:
- Revert the observability wiring and dependency together, leaving the runtime on the no-op path and removing the added env contract/documentation in the same rollback.

## Open Questions

- Should the first version trace full user-visible response text, or only request/query/tool metadata plus error details?
- Should the repository expose one service name for all agent surfaces, or distinguish CLI, Streamlit, and future HTTP adapters in observability metadata from the start?
