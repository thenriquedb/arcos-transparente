## 1. Shared XML decoding contract

- [x] 1.1 Replace the forced `ISO-8859-1` constant in `ingestion/parsers/xml/shared.py` with helpers that resolve source encoding from BOM or XML declaration before decoding.
- [x] 1.2 Keep `ISO-8859-1` as the explicit fallback only when the XML source does not provide a usable encoding declaration.
- [x] 1.3 Raise descriptive errors when a declared encoding is unsupported or when the file bytes cannot be decoded with the declared codec.

## 2. Parser and ingestion integration

- [x] 2.1 Route all XML parser entrypoints that currently use `read_xml_text`, `parse_xml_root`, or raw XML serialization through the new declaration-aware decoding path.
- [x] 2.2 Preserve the current sanitization behavior by applying invalid-character cleanup after decoding with the resolved encoding and before parsing or persistence.

## 3. Regression coverage

- [x] 3.1 Add shared XML helper tests for BOM/declaration-based decoding, missing declarations, unsupported encodings, and declared-encoding decode failures.
- [x] 3.2 Update parser or pipeline regression tests to prove correctly declared UTF-8 and `ISO-8859-1` XML inputs both import without mojibake and keep `xml_original` sanitized.

## 4. Documentation

- [x] 4.1 Update `docs/importacao.md` and any nearby ingestion guidance to describe the new contract: respect XML-declared encoding, otherwise fall back to `ISO-8859-1`.
- [x] 4.2 Document the failure behavior for invalid or unsupported declared encodings so future maintainers do not reintroduce silent codec fallbacks.
