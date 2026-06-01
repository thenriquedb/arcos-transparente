## 1. Shared Context Anchors

- [x] 1.1 Define a shared guardrail helper for recent allowed public-context anchors and the generic follow-up shapes that can reuse them.
- [x] 1.2 Thread prior allowed user-query context through `agents/chatbot/core.py` and `agents/router.py` so supported entrypoints evaluate the same anchor chain.
- [x] 1.3 Ensure blocked, empty, and unrelated turns do not establish or revive reusable public-context anchors.

## 2. Cross-Scope Follow-Up Admission

- [x] 2.1 Extend `agents/guardrails.py` to admit concise contextual follow-ups across representative supported domains instead of relying on isolated scope-specific heuristics.
- [x] 2.2 Add domain-aware validation for reused filters such as year, entity, object, and scope-local refinements without over-admitting unrelated ellipses.
- [x] 2.3 Keep ambiguous anchored follow-ups inside the public-data flow so the lower orchestration layer can clarify instead of returning an out-of-scope refusal.

## 3. Regression Coverage

- [x] 3.1 Add guardrail tests covering positive and negative contextual follow-ups for multiple domain families, including contracts, receitas, and at least one additional non-contract scope.
- [x] 3.2 Add chatbot session tests for `ask()` and `stream()` that verify contextual follow-up continuity and broken-anchor behavior after unrelated or blocked turns.
- [x] 3.3 Add compatibility-wrapper regression coverage proving the same documented contextual follow-up is admitted consistently across supported entrypoints.

## 4. Verification And Documentation

- [x] 4.1 Update operator-facing documentation if the documented follow-up/clarification contract changes for supported public-data conversations.
- [x] 4.2 Run the relevant automated test suite and confirm the new cross-scope contextual follow-up matrix passes.
