## 1. Inventory And Target Layout

- [ ] 1.1 Inventory duplicated pure helpers across ingestion schemas and SQL tool schema/filter modules.
- [ ] 1.2 Classify each helper family as top-level shared or subsystem-local shared based on actual reuse scope.
- [ ] 1.3 Define the target shared module layout and file destinations before moving callers.

## 2. Shared Module Extraction

- [ ] 2.1 Extract the cross-cutting helper families that belong in top-level `shared/` modules.
- [ ] 2.2 Create subsystem-local shared helpers for ingestion-only or SQL-tool-only utility families that should not live in global `shared/`.
- [ ] 2.3 Keep domain-specific business logic local and extract only the generic sub-parts from mixed helpers.

## 3. Caller Migration

- [ ] 3.1 Update ingestion schema modules to import the extracted shared helpers and remove their local duplicates.
- [ ] 3.2 Update SQL tool schema/filter modules to import the extracted shared helpers and remove their local duplicates.
- [ ] 3.3 Verify representative callers still produce the same normalization, parsing, and metadata behavior after migration.

## 4. Regression Coverage

- [ ] 4.1 Add or update direct tests for the new shared helper families.
- [ ] 4.2 Add or update representative caller tests covering migrated ingestion and SQL tool modules.
- [ ] 4.3 Confirm that extracted helpers preserve current accepted/rejected input behavior and metadata output shape.

## 5. Documentation And Cleanup

- [ ] 5.1 Document the placement rule for top-level shared helpers versus subsystem-local shared helpers.
- [ ] 5.2 Remove leftover dead helpers or compatibility wrappers that are no longer needed after the migration.
