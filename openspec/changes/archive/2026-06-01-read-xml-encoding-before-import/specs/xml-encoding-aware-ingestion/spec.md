## ADDED Requirements

### Requirement: XML ingestion resolves source encoding before decoding parser input
The system SHALL resolve XML source encoding from the file itself before decoding parser input, honoring a supported BOM or XML declaration when present and falling back to `ISO-8859-1` only when no usable source encoding is declared.

#### Scenario: Declared UTF-8 is preserved during import
- **WHEN** an ingestion parser processes an XML file whose declaration advertises `UTF-8`
- **THEN** the shared XML reader decodes the file as UTF-8 before parser-specific extraction runs
- **AND** extracted text preserves characters that would be corrupted by a forced `ISO-8859-1` decode

#### Scenario: Missing declaration uses legacy fallback
- **WHEN** an ingestion parser processes an XML file with no BOM and no `encoding` attribute in the XML declaration
- **THEN** the shared XML reader decodes the file using `ISO-8859-1`
- **AND** all parser entrypoints receive text under the same fallback contract

### Requirement: XML ingestion fails clearly for unusable declared encodings
The system SHALL reject XML inputs whose declared encoding cannot be resolved or cannot decode the source bytes, instead of silently retrying with a different codec.

#### Scenario: Unsupported declared encoding stops the import
- **WHEN** an XML file declares an encoding name that the runtime cannot resolve
- **THEN** the shared XML reader raises a descriptive error that identifies the problematic declaration
- **AND** the import does not continue with a fallback codec

#### Scenario: Declared encoding mismatch stops the import
- **WHEN** an XML file declares a supported encoding but its bytes cannot be decoded with that codec
- **THEN** the shared XML reader raises a descriptive decode error
- **AND** the import does not silently replace the declared codec with `ISO-8859-1` or another fallback

### Requirement: Sanitization happens after declaration-aware decoding
The system SHALL continue removing invalid control characters from XML-derived text after decoding with the resolved source encoding, so valid declared characters are preserved while unsafe text still cannot be persisted.

#### Scenario: Valid decoded characters remain while invalid controls are removed
- **WHEN** an XML file is decoded using its resolved source encoding and the resulting text contains invalid control characters
- **THEN** sanitization removes only the invalid control characters before parsing and persistence
- **AND** valid visible characters from the resolved encoding remain intact in extracted fields and stored raw XML snapshots
