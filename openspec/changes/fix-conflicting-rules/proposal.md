## Why

The project currently defines agent behavior in multiple overlapping layers: deterministic router heuristics, the system prompt, tool docstrings and return hints, and separate chatbot versus legacy entrypoints. These layers do not currently share one clear precedence model, which creates contradictory behavior, duplicated policy, and inconsistent safeguards depending on how a question enters the system.

## What Changes

- Define an explicit precedence order for behavioral rules across hard-coded guardrails, system prompt instructions, tool contracts, and compatibility routing logic.
- Align the chatbot and any remaining legacy entrypoints so non-negotiable rules are enforced consistently before model execution.
- Audit and remove conflicting or duplicated rule definitions where the same query behavior is described differently in router logic, prompt text, or tool-level guidance.
- Clarify which layer owns conversational interpretation, which layer owns hard safety constraints, and which layer exists only for compatibility.
- Add regression coverage for representative rule-conflict cases so future prompt or tool changes do not silently reintroduce contradictions.

## Capabilities

### New Capabilities
- `agent-rule-consistency`: Defines how conflicting rules are resolved across guardrails, prompt instructions, tool contracts, and compatibility routing so the assistant behaves consistently across entrypoints.

### Modified Capabilities
- None.

## Impact

- Affected code: `agents/chatbot/*`, `agents/router.py`, agent bootstrap/configuration modules, and selected SQL tool modules.
- Affected behavior: guardrail enforcement, query interpretation ownership, cross-tool chaining expectations, and consistency between chatbot and non-chatbot entrypoints.
- Affected docs: `docs/agent-system-prompt.md` and any architecture/operator documentation describing runtime behavior.
- Risk areas: accidental weakening of safety checks, prompt/tool drift, and regressions in previously working query flows while rule ownership is being untangled.
