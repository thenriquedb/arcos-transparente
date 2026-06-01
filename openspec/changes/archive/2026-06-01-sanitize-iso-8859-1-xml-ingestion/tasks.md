## 1. Shared XML Input Contract

- [x] 1.1 Create a shared ingestion XML helper that reads files as `ISO-8859-1` and returns sanitized text or parsed XML roots for parser consumers.
- [x] 1.2 Implement the invalid-character sanitization helper used by the shared XML input path, preserving valid Latin text and normal whitespace.
- [x] 1.3 Add direct unit coverage for the shared decode-and-sanitize helpers with representative accented text and invalid control characters.

## 2. Parser Adoption

- [x] 2.1 Update all `ingestion/parsers/xml/` implementations that currently rely on `ET.parse`, manual `open(..., encoding=...)`, or `cp1252` fallback to use the shared `ISO-8859-1` input contract.
- [x] 2.2 Keep existing parser field-mapping behavior intact while routing `xml_original` and any parser-specific raw-text access through the sanitized shared input path.
- [x] 2.3 Add or update parser regression tests for representative sources such as contratos, licitacoes, planejamentos, quadro pessoal, and frotas.

## 3. Persistence Safety

- [x] 3.1 Apply recursive text sanitization inside `ingestion/loaders/sql_loader.py` so generic loader-based entities cannot persist invalid characters.
- [x] 3.2 Apply the same sanitization guarantee to the custom contracts persistence flow in `ingestion/pipeline.py`, including nested child rows and `xml_original`.
- [x] 3.3 Verify that persisted values remain unchanged except for removal of invalid characters.

## 4. End-To-End Verification And Documentation

- [x] 4.1 Add pipeline or integration-style tests proving the database never stores invalid characters from XML-derived payloads.
- [x] 4.2 Document the new XML ingestion contract so future parsers default to `ISO-8859-1` decoding and shared sanitization.
- [x] 4.3 Run the relevant parser, pipeline, and loader test suites and fix any regressions introduced by the new contract.
