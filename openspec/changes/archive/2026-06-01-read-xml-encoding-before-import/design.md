## Context

The current shared XML reader in `ingestion/parsers/xml/shared.py` decodes every file as `ISO-8859-1` before sanitization and parsing. That behavior was introduced to standardize ingestion, but it now overrides the source contract declared in XML headers and can silently distort content when a file is authored as UTF-8 or another supported encoding.

This change is cross-cutting because every XML parser goes through the shared helper, and the current documentation in `docs/importacao.md` explicitly tells future parsers to rely on forced `ISO-8859-1`. Any fix therefore needs one shared decoding policy, clear fallback behavior, and regression coverage across parser and pipeline entrypoints.

## Goals / Non-Goals

**Goals:**
- Resolve XML source encoding before decoding parser input, using the source declaration when available.
- Preserve the existing sanitization guarantee after decoding so invalid control characters still never reach persistence.
- Keep legacy ingestion functional by defining a deterministic fallback when the declaration is missing.
- Make future parser guidance match the new shared decoding contract.

**Non-Goals:**
- Changing field mappings, business rules, or database schemas for any ingestion entity.
- Adding broad charset-detection heuristics based on statistical guessing of content bytes.
- Relaxing the invalid-character sanitization guarantees added in the current ingestion flow.

## Decisions

### 1. Centralize encoding resolution in the shared XML helper

The shared helper will stop exposing a single hard-coded `XML_SOURCE_ENCODING` contract and instead resolve an encoding for each file before decoding. The resolution order will be:

1. honor a supported BOM when present;
2. otherwise inspect the XML declaration for `encoding="..."`;
3. otherwise fall back to `ISO-8859-1`.

This keeps all parser entrypoints consistent while preserving compatibility for files that omit the declaration today.

Alternatives considered:
- Keep forcing `ISO-8859-1`: rejected because it ignores the source contract and is the behavior being corrected.
- Let each parser choose its own encoding behavior: rejected because it reintroduces inconsistency across parser families.
- Guess the encoding from content bytes: rejected because probabilistic detection would make imports harder to reason about and test.

### 2. Fail explicitly when the declared encoding cannot be used

When a file declares an unsupported encoding or decoding fails under the declared codec, the shared helper should raise a descriptive import error instead of silently retrying with another codec. Silent fallback after a conflicting declaration would turn bad inputs into mojibake and make data-quality issues harder to detect.

Alternatives considered:
- Retry with `ISO-8859-1` after decode failure: rejected because it would mask bad upstream files and violate the declared source contract.
- Drop invalid bytes during decoding: rejected because the ingestion pipeline should not silently lose content.

### 3. Keep sanitization after decoding, not before

The existing sanitization step remains valuable, but it should operate on correctly decoded text. This preserves the no-invalid-characters guarantee while ensuring valid characters from UTF-8, `ISO-8859-1`, or other supported declared encodings are not altered by a premature fallback decode.

Alternatives considered:
- Sanitize raw bytes before decoding: rejected because byte-level cleanup cannot distinguish encoding boundaries safely.
- Remove sanitization from the XML helper: rejected because downstream persistence still depends on shared text safety.

### 4. Update parser-facing documentation and tests with the new contract

The implementation will update docs and tests so the shared expectation becomes “respect XML-declared encoding, else use legacy fallback.” This prevents future parsers from reintroducing forced-decoding logic and makes the migration discoverable for maintainers.

## Risks / Trade-offs

- [Risk] Some XML files may currently import “successfully” only because forced `ISO-8859-1` masks a wrong or stale declaration. → Mitigation: make decode failures explicit and cover representative fixtures in parser tests.
- [Risk] Supporting declaration-aware decoding increases complexity in the shared helper. → Mitigation: keep all resolution logic isolated in one helper with focused unit tests for BOM, declaration, fallback, and failure cases.
- [Risk] Documentation and prior assumptions still reference forced `ISO-8859-1`. → Mitigation: update import docs and change notes alongside the code change.

## Migration Plan

1. Implement shared helpers to resolve encoding from BOM and XML declaration before decoding.
2. Route all XML parser entrypoints through the new helper without changing parser-specific extraction logic.
3. Update docs and regression tests to cover declared UTF-8, declared `ISO-8859-1`, missing declarations, and invalid declarations.
4. Roll back by restoring the forced `ISO-8859-1` reader if unexpected real-world files require the previous behavior temporarily.

## Open Questions

- None at proposal time; the fallback policy is intentionally fixed to `ISO-8859-1` when the declaration is absent so implementation can proceed without additional product decisions.
