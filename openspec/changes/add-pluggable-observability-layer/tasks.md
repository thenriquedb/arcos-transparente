## 1. Observability Contract And Configuration

- [x] 1.1 Create a shared observability package for the chatbot runtime with the provider-neutral interfaces, sanitized event model, and a no-op implementation.
- [x] 1.2 Add environment-backed observability configuration parsing and validation for `OBSERVABILITY_ENABLED`, `OBSERVABILITY_PROVIDER`, and required `LANGSMITH_*` settings.
- [x] 1.3 Implement the observability provider factory and wire LangSmith as the first concrete adapter without making the core runtime import LangSmith-specific APIs directly.
- [x] 1.4 Update bootstrap wiring so chatbot runtime construction receives the resolved observability provider alongside existing agent/runtime dependencies.

## 2. Runtime Instrumentation

- [x] 2.1 Instrument `ChatbotApplication` request lifecycle boundaries for request start/end, deterministic policy outcomes, backend invocation, streaming fallback, and surfaced failures.
- [x] 2.2 Instrument hybrid tool selection outcomes, including selected candidates, clarify/block actions, and fallback reason codes, through the shared observability contract.
- [x] 2.3 Add registry-level public-tool wrapping so tool start, success, and error stages are observable without editing each SQL or RAG tool module.
- [x] 2.4 Ensure observability payloads use the allowlisted runtime event model and never emit secrets or raw provider credentials.

## 3. Documentation And Verification

- [x] 3.1 Add the LangSmith dependency and update `.env.example`, `README.md`, and relevant architecture/runtime docs with the canonical observability contract and opt-in behavior.
- [x] 3.2 Add focused tests for disabled observability, supported LangSmith configuration, missing required LangSmith settings, and unsupported observability providers.
- [x] 3.3 Add runtime and registry tests that verify lifecycle events are emitted through the shared provider boundary for blocked queries, allowed queries, tool execution, and failure paths.
- [x] 3.4 Run the focused chatbot/runtime test suites and verify the documented env contract matches the implemented observability bootstrap behavior.
