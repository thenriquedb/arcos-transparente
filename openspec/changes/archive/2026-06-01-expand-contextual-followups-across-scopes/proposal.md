## Why

The chatbot now blocks fewer in-scope public-data questions at the pre-model guardrail boundary, but contextual continuity still works only for a narrow subset of follow-up shapes and domains. After recent guardrail tightening, users can get a correct answer for an initial transparency question and then have a natural refinement such as `E o de 2025?` rejected as out of scope, which breaks normal conversational use across the broader municipal-data surface.

## What Changes

- Extend hard pre-agent guardrail admission so short contextual follow-ups can reuse prior in-scope public-data context instead of being treated as fresh out-of-scope queries.
- Generalize contextual follow-up support across all supported municipal transparency scopes, including servidores, folha, contratos, licitacoes, despesas, receitas, planejamento, patrimonios, quadro de pessoal, and eleitos.
- Define safe context anchoring rules so follow-ups inherit only from prior allowed public-data turns and never from blocked, empty, or unrelated out-of-scope requests.
- Define fallback behavior when context is insufficient or ambiguous, so the chatbot asks for clarification or keeps the guardrail instead of guessing.
- Add regression coverage for contextual follow-ups across direct chatbot entrypoints and compatibility guardrail wrappers.

## Capabilities

### New Capabilities
- `public-contextual-followups`: Defines when the citizen-facing assistant may accept concise follow-up questions by reusing prior allowed public-data context across supported domains.

### Modified Capabilities
- `agent-rule-consistency`: Hard guardrail behavior must admit documented in-scope contextual follow-ups consistently across supported entrypoints instead of rejecting them as out of scope.

## Impact

- Affected code: `agents/guardrails.py`, `agents/chatbot/core.py`, `agents/router.py`, routing extractors/helpers, and tool-facing context handling where domain follow-ups need normalization.
- Affected behavior: session continuity, follow-up admission, clarification handling, and cross-entrypoint consistency for concise contextual refinements.
- Affected tests: guardrail, chatbot, router, and representative domain-level conversation regressions.
- Risk areas: accidentally over-admitting out-of-scope ellipses, inheriting the wrong prior context, or creating inconsistent follow-up behavior between domains.
