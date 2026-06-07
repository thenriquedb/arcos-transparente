## 1. Runtime Contract Consolidation

- [ ] 1.1 Refactor `agents/chatbot/agent.py` so chatbot bootstrap reads provider, model, and API key from the canonical environment contract and no longer depends on hard-coded runtime defaults.
- [ ] 1.2 Update agent-facing error surfaces such as `agents/chatbot/web.py` to reference the canonical env contract and current OpenAI-only provider support.
- [ ] 1.3 Extend `tests/agents/test_chatbot.py` with coverage for configured bootstrap success, missing `OPENAI_MODEL`, missing `OPENAI_API_KEY`, unsupported `LLM_PROVIDER`, and any compatibility fallbacks retained for old aliases.

## 2. Example Env And Documentation

- [ ] 2.1 Create a root `.env.example` that includes the chatbot settings `LLM_PROVIDER`, `OPENAI_MODEL`, and `OPENAI_API_KEY` alongside the existing core local-project env entries needed for setup.
- [ ] 2.2 Update `README.md` so the onboarding flow tells contributors to create `.env` from the example file and documents the canonical agent env variables.
- [ ] 2.3 Update any directly conflicting agent-bootstrap docs, such as `docs/arquitetura-agent-tools.md` and `docs/codex-cli-contexto.md`, so internal documentation matches the runtime contract.

## 3. Verification

- [ ] 3.1 Run the focused chatbot test suite and fix any failures caused by the env-contract consolidation.
- [ ] 3.2 Manually verify that the example env file and README describe the same provider, model, and API-key settings enforced by the bootstrap code.
