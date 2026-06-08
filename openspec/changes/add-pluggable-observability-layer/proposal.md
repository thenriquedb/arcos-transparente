## Why

The chatbot runtime currently has no first-class observability boundary for tracing agent execution, tool calls, selector decisions, or failures end to end. If we add LangSmith directly inside the runtime flow now, we risk scattering provider-specific code through the chatbot bootstrap and making a later migration to Langfuse or another tracing backend expensive.

## What Changes

- Introduce a provider-neutral observability layer for the chatbot and agent runtime, with a no-op default and a LangSmith-backed implementation as the first concrete adapter.
- Instrument the main runtime boundaries that matter for diagnosis and operations: deterministic policy, hybrid tool selection, agent invocation, tool execution lifecycle, streaming and fallback paths, and surfaced failures.
- Keep observability wiring outside of domain tool logic so SQL tools, RAG tools, router compatibility, and chat orchestration remain usable without a hard dependency on LangSmith.
- Add an environment-driven configuration contract for enabling observability, selecting the active observability provider, and passing provider-specific credentials/settings without forcing them into the main agent bootstrap path.
- Document the observability contract and extension path so a future Langfuse adapter can be added by implementing the same interface instead of rewriting the runtime.

## Capabilities

### New Capabilities
- `agent-observability`: Define the provider-neutral tracing and observability contract for chatbot runtime events, no-op behavior, and pluggable provider adapters such as LangSmith.

### Modified Capabilities
- `agent-runtime-configuration`: Extend the runtime configuration contract to cover observability enablement, provider selection, and provider-specific environment settings/documentation.

## Impact

- Affected code: `agents/chatbot/agent.py`, `agents/chatbot/core.py`, selector and policy integration points, and new shared observability modules at the chatbot runtime boundary.
- Affected docs: `README.md`, `.env.example`, architecture/runtime docs, and any operator-facing setup docs that describe agent bootstrapping.
- Affected dependencies: add the LangSmith client/runtime integration required for the first adapter while keeping the abstraction open for other providers.
- Operational impact: local and deployed environments may opt into tracing with new observability env vars, but the runtime must continue to work unchanged when observability is disabled or unconfigured.
