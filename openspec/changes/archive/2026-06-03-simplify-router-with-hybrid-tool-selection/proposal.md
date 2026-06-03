## Why

The current router still encodes a large amount of domain interpretation through keyword lists, extractors, and precedence chains, which makes every new query pattern expensive to maintain and easy to regress. We need a more scalable routing approach that keeps hard safety and UX-critical rules deterministic while moving domain and tool-family selection to a more flexible model-driven layer.

## What Changes

- Replace deterministic per-domain routing for the citizen-facing chat path with a hybrid tool-selection layer that combines hard guardrails with structured LLM-based candidate selection.
- Stop deriving tool arguments from router heuristics for the main chat flow; the selector will narrow the candidate tool set and let the agent decide how to use those tools at runtime.
- Enrich public tool registration with routing metadata such as examples and selection hints so new tools can be onboarded without expanding keyword chains.
- Keep deterministic handling only for non-negotiable behaviors such as prompt-injection blocking, obviously out-of-scope requests, contextual follow-up admission, and acronym/clarification safety.
- **BREAKING** Remove the current router facade from the primary chatbot execution path and demote deterministic domain routing to a compatibility concern outside the main citizen-facing runtime.

## Capabilities

### New Capabilities
- `hybrid-tool-selection`: Selects a small set of public-tool candidates for an allowed citizen query using structured LLM output plus tool metadata, while preserving deterministic safety and clarification gates.

### Modified Capabilities
- `agent-rule-consistency`: Changes the ownership model so compatibility routing is no longer the authoritative mechanism for allowed-query interpretation in the citizen-facing chatbot.

## Impact

- Affected code: `agents/chatbot/*`, `agents/guardrails.py`, `agents/router.py`, `agents/routing/*`, `agents/tools/registry.py`, and tests that assert deterministic route payloads.
- Affected behavior: how the chatbot narrows tools, when it asks clarifying questions, how new public tools become routable, and how compatibility-only routing is isolated from the main runtime.
- Affected APIs/contracts: public tool registration metadata, pre-agent selection contracts, and internal diagnostics about selected tools and fallback behavior.
- Risk areas: regressions in domain disambiguation, overly broad or overly narrow candidate selection, and accidental loss of deterministic protections during the router simplification.
