## Context

The behavior audit (`docs/auditoria-comportamento-core.md`) identified six semantic/product defects in the citizen-facing chatbot's interpretation layer. They span three coordination points that must agree but currently don't: the routing/extraction heuristics (`agents/routing/extractors.py`, `agents/routing/hybrid_selection.py`), the tool contracts/schemas (`contracts/shared/filters.py`, `despesas_por_funcao.py`), and the system prompt (`docs/agent-system-prompt.md`).

Five of the six defects are localized heuristic/prompt mismatches with low blast radius. One (finding 2, contract vigência) requires a real tool-contract change because the public `ContratosFiltroSchema` cannot express in-force filtering at all today — `data_fim` exists on the model (`ALLOWED_CONTRACT_FIELDS`) but is not exposed as a filter.

Each fix is independent; they share no state and can land as separate commits with their own regression tests.

## Goals / Non-Goals

**Goals:**
- Make generic search verbs, event/show spend, travel spend, function-spend totals, and named festivals behave as the citizen expects, per the audit's "comportamento esperado" for each finding.
- Add a vigência filter so "contratos ativos hoje" can be computed as an in-force interval.
- Add regression tests that pin each corrected behavior and guard against over-correction.

**Non-Goals:**
- No architecture, style, or broad refactor of the routing layer (the audit explicitly excludes these).
- No change to the hybrid-selection fallback architecture or the deterministic policy gate ordering.
- No new tools or domains; only existing tool contracts and heuristics are adjusted.

## Decisions

**1. Search verbs (finding 1): tighten extraction, don't add a new gate.**
Remove the `pesquise|busque|procure` catch-all pattern from `_extract_nome_para_historico`, or require a concomitant salary/payment term and reject candidates beginning with domain nouns (contrato, licitação, despesa, diária…). Chosen over adding a new negative router rule because the defect is the extractor producing a false name; fixing it at the source also repairs `_query_establishes_public_context`, which reuses the same extractor. Alternative (downstream filtering in `_select_salary_history_with_router`) was rejected — it would leave the corrupted public-context guardrail untouched.

**2. Contract vigência (finding 2): extend the schema, then fix the year heuristic.**
Add `data_fim` bounds (or an `em_vigencia_em`/in-force-on-date parameter) to `ContratosFiltroSchema`, then change `_extract_contratos_active_year_filters` and the prompt rule (`agent-system-prompt.md:58`) to map "ativos/atuais/hoje" to `data_inicio ≤ hoje ≤ data_fim` (fim null = open-ended). The schema change is the prerequisite — without it the correct semantics are inexpressible. Chosen the interval semantics (`fim ≥ hoje OR fim IS NULL`) over a single "ends after today" filter so open-ended contracts are not dropped.

**3. Event/show spend (finding 3): generalize the special case.**
Give `evento(s)`/`show(s)` the same fallback treatment `festival` already has, or remove them from `_GENERIC_PUBLIC_OBJECT_TOKENS` rejection when a spend signal is present, so `_extract_licitacoes_objeto` returns an object and `_select_event_spend_query` fires the cross-source fan-out. Chosen over hard-coding more phrases (the current `"shows e eventos"` literal is exactly the brittleness we're removing).

**4. Travel spend (finding 4): align keywords with the published hint.**
Either drop `"viagem"` from the `consultar_diarias` hint (so it stops implying coverage) or treat "viagem/viagens + gasto" as the combined diárias+passagens path. Chosen the combined path: the citizen's "custo de viagem" normally means diárias + passagens, and the tool already advertises the hint. Implementation: add `viagem/viagens` recognition so `_select_travel_spend_query` no longer requires both keyword sets to be independently present.

**5. Function-spend totals (finding 5): keep the four-stage rule dominant.**
In the despesas-por-função domain, stop letting a lone "total" make `_is_explicit_aggregate_spend_request` force the single-metric aggregate. Either keep `_select_broad_spend_query` engaged for function spend, or make `agregar_despesas_por_funcao` return the sum of all four stages for broad "gasto". Chosen keeping the four-stage display rule dominant (prompt + routing) over changing the aggregator default, to avoid changing the aggregator's contract for callers that legitimately want a single metric.

**6. Named festivals (finding 6): preserve qualified phrases.**
In `_extract_public_object_candidate`, when "festival" is followed by qualifier words, keep the full phrase as the object and do not overwrite a user-supplied year; only the bare "festival" falls back to the gastronômico/2025 prompt assumption (`agent-system-prompt.md:182,188`).

## Risks / Trade-offs

- [Over-correcting finding 1 could break legitimate "salário do X" routing] → keep a regression that asserts "Salário do João Silva" still routes to payroll.
- [Finding 2 schema change touches a public tool contract used by other queries] → add `data_fim` as additive/optional; existing `data_inicio`-only queries keep working unchanged.
- [Combining diárias+passagens for "viagens" (finding 4) widens the candidate set and could surprise users expecting one number] → spec permits a single clarification as an acceptable alternative; pick combined fan-out only when a spend signal is present.
- [Finding 5 four-stage rule may conflict with users who genuinely want one aggregated number] → scope the rule to broad function-spend ("gasto/custo/total com [função]"); explicit single-metric requests are out of scope.

## Migration Plan

No data migration. Changes are code + prompt only and ship behind normal deploy. Each finding is an independent commit with its own tests; rollback is per-commit revert. The `ContratosFiltroSchema` change is additive (new optional filter), so no consumer migration is required.

## Open Questions

- Finding 4: combined fan-out vs. a single clarification question — default to combined fan-out unless product prefers clarification.
- Finding 2: expose raw `data_fim` bounds vs. a single `em_vigencia_em` date parameter — leaning to `data_fim` bounds for consistency with existing `data_inicio*` naming; confirm during implementation.
