## Context

The chatbot bootstrap in `agents/chatbot/agent.py` already reads some environment variables, but it still mixes hard-coded defaults with multiple alias names and documentation that has drifted from runtime behavior. Today the README, architecture docs, and Codex context doc do not fully agree on which variables matter or which model is the default.

This change is intentionally narrow: it standardizes how the chatbot runtime receives provider, model, and API-key configuration through `.env`, adds a checked-in `.env.example`, and aligns setup documentation with the actual bootstrap contract. The current supported provider remains OpenAI.

## Goals / Non-Goals

**Goals:**
- Make the chatbot bootstrap depend on a single documented set of environment variables for provider, model, and API key.
- Remove ambiguity caused by code defaults and duplicate alias names for the same agent setting.
- Add a root `.env.example` that makes local setup discoverable without reading source code.
- Update developer-facing docs so they describe the same environment contract enforced by runtime validation.

**Non-Goals:**
- Adding support for new LLM providers beyond the currently supported OpenAI path.
- Reworking RAG embedding configuration or unrelated project environment variables.
- Introducing a full configuration framework or secret manager abstraction.

## Decisions

### 1. Use one canonical chatbot env contract and validate it explicitly
The chatbot bootstrap will read a single documented set of variables for its runtime configuration and fail fast when any required setting is missing or invalid.

Chosen direction:
- `LLM_PROVIDER` for provider selection
- `OPENAI_MODEL` for the chat model name
- `OPENAI_API_KEY` for credentials

Why:
- These names are already close to the current runtime and documentation, so the migration is small.
- They avoid introducing a second large rename just to support hypothetical future providers.
- They let `.env.example` become the source of truth instead of hard-coded defaults in Python.
- The implementation may keep short compatibility fallbacks for `MODEL_PROVIDER` and `AGENT_MODEL`, but docs and validation messages will treat `LLM_PROVIDER` and `OPENAI_MODEL` as the only canonical names.

Alternatives considered:
- Keep hard-coded defaults and only add `.env.example`: rejected because code and docs can drift again.
- Introduce provider-agnostic `AGENT_*` variables now: rejected because the runtime is still OpenAI-only and this would expand scope without delivering user-requested value today.

### 2. Keep provider support narrow but make provider configuration explicit
The runtime will continue to accept only `openai` as the supported provider value, but the provider must still come from the environment contract and be validated with a clear error.

Why:
- The request is about configuration externalization, not multi-provider implementation.
- Explicit provider validation preserves a clean upgrade path for future provider additions.

Alternatives considered:
- Remove the provider variable entirely and hard-code `openai`: rejected because the user explicitly asked to define the provider through `.env`.
- Pretend to support multiple providers without implementation: rejected because it would create a misleading contract.

### 3. Make `.env.example` and README the onboarding source of truth
The repository will include a root `.env.example` that shows the minimum local setup, and the README will direct contributors to copy or adapt it before running the chatbot.

Why:
- New contributors should not need to inspect `agents/chatbot/agent.py` to discover required settings.
- The example file reduces setup mistakes and makes defaults visible in version control.

Alternatives considered:
- Document only in README: rejected because example env scaffolding is easier to apply and maintain.
- Update only internal docs: rejected because the README is the main onboarding entrypoint.

## Risks / Trade-offs

- [Existing local environments rely on old alias behavior] → Decide whether to keep a short compatibility fallback or update all references in one pass, and cover the chosen contract with tests.
- [OpenAI-specific variable names may feel inconsistent with a generic provider field] → Keep the design explicit that OpenAI remains the only supported provider in this phase.
- [Docs can drift again if future config changes skip README and `.env.example`] → Add regression coverage for env validation and treat `.env.example` as a required artifact of runtime config changes.

## Migration Plan

1. Update the chatbot bootstrap to validate a single canonical env contract.
2. Adjust tests to exercise the new required variables and unsupported-provider errors.
3. Add `.env.example` with the chatbot configuration and existing core project env entries.
4. Update README and any directly conflicting bootstrap docs to match the new contract.

Rollback:
- Revert the bootstrap validation and docs changes together so runtime and onboarding remain aligned.
