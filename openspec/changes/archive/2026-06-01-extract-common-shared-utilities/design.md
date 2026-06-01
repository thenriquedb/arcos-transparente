## Context

The repository already contains `shared/utils/validation.py` and `shared/utils/text.py`, but common pure helper behavior is still duplicated in multiple places:

- ingestion schemas repeat text-normalization validators and small parsing helpers such as local integer conversion,
- SQL tool filter/schema modules repeat field-list normalization, metadata serialization, and range-validation patterns,
- similar helper semantics are implemented near call sites instead of being centralized by ownership.

The result is a codebase that already wants shared utilities, but does not yet apply a consistent extraction rule. This change is about organizing those common methods and functions into separated shared folders without changing business behavior.

## Goals / Non-Goals

**Goals:**
- Extract duplicated pure helper logic into shared modules with clear scope boundaries.
- Reuse the existing `shared/` pattern instead of introducing ad-hoc local duplicates.
- Define where cross-cutting helpers belong versus where bounded-context shared helpers belong.
- Preserve current parsing, normalization, and metadata behavior at call sites.
- Add regression coverage so shared extraction remains behavior-preserving.

**Non-Goals:**
- Rewriting domain-specific business rules into generic abstractions.
- Creating a large framework of inheritance-heavy utility base classes if plain functions are sufficient.
- Changing public behavior, validation semantics, or output formats as part of the refactor.
- Extracting one-off helpers that are not meaningfully reused.

## Decisions

### 1. Extract only pure, repeated logic into shared folders

This change will extract helpers only when they are:
- pure or near-pure,
- used in more than one module or class,
- not strongly bound to one domain's business semantics.

Rationale:
- This keeps the refactor focused and low risk.
- Shared code should reduce duplication, not hide domain logic behind generic wrappers.

Alternatives considered:
- Broad refactor of all similar-looking methods: rejected because many methods are only superficially similar and should remain local.
- Base-class-heavy abstraction: rejected because most duplication is functional helper logic, not lifecycle behavior.

### 2. Use scope-based placement rules for shared code

The implementation will separate shared folders by ownership:

- Top-level `shared/` for cross-cutting helpers used by multiple subsystems, such as generic validation, parsing, and text normalization.
- Subsystem-local `shared/` folders for helpers reused only inside one bounded area, such as ingestion-only schema utilities or SQL-tool-only schema/filter helpers.

Rationale:
- Not every shared helper should live in the global `shared/` package.
- Local shared folders keep bounded-context utilities close to their consumers.

Alternatives considered:
- Put everything in top-level `shared/`: rejected because it would flatten boundaries and encourage over-generalization.
- Keep all helpers local to the first module that needed them: rejected because that preserves the current duplication problem.

### 3. Favor helper functions over generalized classes

Shared extraction will prefer small functions such as:
- text/integer/field normalization helpers,
- metadata dump helpers,
- common validation routines for repeated schema patterns.

New shared classes or mixins should be introduced only when multiple callers truly need the same structured behavior and the abstraction remains simpler than repeated standalone functions.

Rationale:
- The codebase already uses Pydantic validators heavily; functions integrate cleanly without forcing inheritance.
- Function extraction is easier to review and safer to adopt incrementally.

Alternatives considered:
- Introduce generic schema base classes for every family of validators: rejected because it increases coupling and indirection.

### 4. Preserve external behavior during extraction

Refactored callers must keep the same effective behavior for:
- accepted/rejected values,
- normalized outputs,
- error semantics where tests or callers depend on them,
- metadata payload structure.

Rationale:
- This change is a maintainability refactor, not a behavioral redesign.
- Stability matters more than maximal deduplication.

Alternatives considered:
- Opportunistically “improve” validation semantics during extraction: rejected because it mixes refactor and behavior change, increasing risk.

### 5. Cover extracted helpers with representative caller tests

Regression coverage will validate both:
- the shared helper behavior itself,
- representative ingestion/schema/tool callers after migration.

Rationale:
- Shared helpers become high-leverage dependencies once extracted.
- Caller-level tests protect against subtle integration drift even when the shared helper passes unit tests.

Alternatives considered:
- Test only the new shared helper modules: rejected because integration mistakes often happen at the adoption layer.

## Risks / Trade-offs

- [Risk] A helper may be extracted too early even though its semantics are still domain-specific. -> Mitigation: require scope-based ownership review before moving code into top-level `shared/`.
- [Risk] Behavior may drift if an extracted helper “simplifies” existing validation edge cases. -> Mitigation: preserve representative caller tests and treat behavior changes as out of scope.
- [Risk] New shared modules may become dumping grounds for unrelated helpers. -> Mitigation: document placement rules and keep subsystem-local shared folders when ownership is narrow.
- [Risk] Refactoring many call sites at once can make review noisy. -> Mitigation: group extraction work by helper family and migrate incrementally.

## Migration Plan

1. Inventory repeated pure helpers across ingestion schemas and SQL tool schema/filter modules.
2. Classify each helper by scope: global shared versus subsystem-local shared.
3. Create the target shared modules and move the extracted logic there.
4. Update callers to import shared helpers and remove the local duplicates.
5. Add or update tests covering the extracted helpers and representative migrated callers.
6. Document the folder-placement rule for future refactors.

Rollback strategy:
- Because this is an internal refactor, rollback is straightforward: revert the extraction changes and restore local helper definitions if a regression appears.

## Open Questions

- Which repeated SQL tool schema patterns justify a shared SQL-tool helper module versus remaining as simple local functions?
- Should ingestion-specific shared helpers live in `ingestion/schemas/shared/` or in a flatter local shared module under `ingestion/`?
- Is there enough current agent/bootstrap duplication to include that family in this change, or should this proposal stay focused on schema and validation helpers only?
