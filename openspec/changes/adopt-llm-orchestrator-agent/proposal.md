## Why

The project currently has two competing agent architectures: a deterministic router-driven path and a chatbot path that already behaves more like a broad tool-using assistant. This split duplicates policy across router heuristics, the system prompt, and tool docstrings, making behavior harder to evolve and leaving the chatbot path without the same hard safeguards as the router path.

## What Changes

- Shift the citizen-facing chatbot architecture to use the LLM as the primary orchestrator for tool selection, follow-up questions, and multi-step query chaining.
- Preserve a small set of hard-coded guardrails for scope, prompt-injection resistance, and other non-negotiable protections before the agent runs.
- Move query interpretation behavior now encoded in router heuristics into prompt and tool contracts where appropriate.
- Align tool contracts and chatbot behavior around cross-domain orchestration flows such as cargo-politico -> eleito -> historico de pagamentos and contrato -> licitacao/despesa follow-ups.
- Reduce the router from runtime decision-maker to a thinner safety and compatibility layer, with a clear boundary between hard invariants and model-managed orchestration.

## Capabilities

### New Capabilities
- `llm-orchestrated-chat`: Defines how the chatbot should interpret public-data questions, choose tools, chain tool calls, preserve conversational context, and enforce hard pre-agent guardrails.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/*`, `agents/router.py`, `main.py`, `agents/tools/registry.py`, selected tool modules and their tests.
- Affected behavior: tool selection, cross-tool chaining, guardrail enforcement, conversational follow-ups, and ambiguity handling.
- Affected docs: agent prompt and architecture documentation for the chatbot/runtime boundary.
- Risk areas: regressions in query classification, loss of deterministic safety checks, and divergence between prompt guidance and tool-level contracts.
