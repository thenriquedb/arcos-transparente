## 1. Deterministic policy boundary

- [x] 1.1 Audit the current guardrail and router helpers to isolate the logic that must remain deterministic in the main chatbot path.
- [x] 1.2 Refactor the pre-agent policy layer so blocked queries, protected acronym clarifications, contextual follow-up admission, and short post-clarification confirmations are resolved before any hybrid selection step.
- [x] 1.3 Add or update tests proving those deterministic policy outcomes never depend on the hybrid selector or downstream agent creation.

## 2. Hybrid tool-selection foundation

- [x] 2.1 Extend public tool registration with the routing metadata required for hybrid selection, including representative examples and selection hints.
- [x] 2.2 Implement a structured hybrid selector module that evaluates an allowed query plus session context against the public-tool catalog and returns `allow`, `clarify`, or `block` decisions.
- [x] 2.3 Implement safe fallback behavior for low-confidence or invalid selector results so the runtime can recover by exposing the full public toolset when needed.

## 3. Chat runtime integration

- [x] 3.1 Integrate the hybrid selector into the citizen-facing chatbot runtime after deterministic policy checks and before agent instantiation.
- [x] 3.2 Update agent bootstrap and runtime wiring so selected candidate tools, clarification outcomes, and fallback behavior are handled explicitly without deterministic route-to-kwargs synthesis.
- [x] 3.3 Add runtime tests covering selected-tool narrowing, clarification before execution, cross-domain candidate sets, and full-toolset fallback behavior.

## 4. Router retirement and compatibility cleanup

- [x] 4.1 Remove deterministic per-domain routing from the main chatbot execution path, including dependence on `ROUTE_PRIORITY_CHAIN` and `_try_route_*` route synthesis for citizen chat.
- [x] 4.2 Delete or isolate remaining router code so only compatibility-safe helpers survive outside the main runtime boundary.
- [x] 4.3 Replace route-payload assertions with behavior-oriented tests that validate candidate coverage, guardrail precedence, and compatibility isolation.

## 5. Documentation and operator guidance

- [x] 5.1 Update architecture and prompt-boundary documentation to describe the new ownership split between deterministic policy, hybrid tool selection, and tool-local execution contracts.
- [x] 5.2 Document the routing metadata contract required for new public tools so future domains can become selectable without central keyword-chain edits.
