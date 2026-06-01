## 1. Guardrail Boundary

- [ ] 1.1 Audit the current chatbot and router entrypoints to isolate the hard pre-agent checks that must remain deterministic.
- [ ] 1.2 Update the chatbot runtime so empty-query, out-of-scope, and prompt-injection checks run before LLM invocation.
- [ ] 1.3 Add or update tests proving blocked queries never invoke the model in the chatbot path.

## 2. Agent Bootstrap Alignment

- [ ] 2.1 Consolidate shared agent bootstrap concerns such as model configuration, prompt loading, and guardrail boundary semantics between `main.py` and `agents/chatbot/agent.py`.
- [ ] 2.2 Preserve broad public tool access for allowed chatbot queries while removing dependence on deterministic per-query tool filtering in the citizen-facing path.
- [ ] 2.3 Decide and codify the compatibility role of `agents/router.py` for non-chatbot or legacy entrypoints.

## 3. Orchestration Contract Migration

- [ ] 3.1 Audit route modules for interpretation rules that must move into prompt guidance, tool docstrings, schemas, or tool-return hints.
- [ ] 3.2 Update the system prompt so it explicitly owns clarification, chaining, and follow-up behavior for the main citizen query patterns covered by this change.
- [ ] 3.3 Strengthen the relevant tool contracts for multi-step flows such as cargo-politico -> eleitos -> historico de pagamentos and contrato -> licitacao/despesa follow-ups.
- [ ] 3.4 Ensure ambiguous person-selection flows return candidates that the chatbot can surface without auto-selecting a match.

## 4. Behavioral Verification

- [ ] 4.1 Replace or downgrade route-centric tests that no longer represent primary runtime behavior.
- [ ] 4.2 Add orchestration-focused tests for cross-domain chaining, conversational follow-ups, and clarification-before-execution rules.
- [ ] 4.3 Add regression coverage for the documented exceptions that should execute without extra time-range clarification.

## 5. Documentation And Rollout

- [ ] 5.1 Update architecture and operator-facing docs to describe the new ownership boundary between hard guardrails and LLM orchestration.
- [ ] 5.2 Document any remaining router compatibility behavior and the intended migration path away from route-driven runtime decisions.
