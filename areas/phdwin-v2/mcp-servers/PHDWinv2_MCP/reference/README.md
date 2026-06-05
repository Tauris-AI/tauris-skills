# PHDWin To Aries Reference Pack

This folder contains conversion reference material copied from `Tauris.PhdWin` so the Cowork MCP package has the context needed for PHDWin-to-Aries review.

## Included

### Tauris-authored Markdown

- `aries-conv-docs/PHDWIN_DATA_MAP.md`
- `aries-conv-docs/ARIES_ACCESS_TABLE_CONTRACTS.md`
- `aries-conv-docs/ARIES_ACCESS_EXPORT_PLAN.md`
- `aries-conv-docs/ARIES_SCHEMA_MAPPING.md`
- `aries-conv-docs/ARIES_AC_PROPERTY_RULES.md`
- `aries-conv-docs/ARIES_CODEBASE_INVENTORY.md`
- `aries-conv-docs/ARIES_EXPORT_RUNNING_LIST.md`
- `aries-conv-docs/ARIES_MIGRATION_ROADMAP.md`
- `aries-conv-docs/AC_ECONOMIC_DEEP_FIDELITY_PLAN.md`
- `aries-conv-docs/LLM_DATABASE_DIAGNOSTIC_PROFILE.md`
- `aries-conv-docs/ARIES_CONVERSION_NEXT_STEPS.md`

### Templates

Raw database templates are intentionally not committed under this plugin area. Cowork rejects plugin archives that contain highly-compressible database blobs over its compression-ratio guard.

Keep cleared Aries `.accdb` templates outside the plugin checkout and point the runtime at them with `ARIES_TEMPLATE_ACCDB_PATH` or the `template_accdb_path` argument. Generate synthetic SQLite fixtures locally after install.

### Cleared PHDWin v2 Reference Documents

- `phdwin-v2/Phdwinout definitions_complete.xls`

Use the PHDWin output definitions spreadsheet as checked-in reference material for PHDWin v2 table/field interpretation and PHDWin-to-Aries mapping review. It is not client data and should not be expanded into copied vendor help/manual content.

## Excluded

The package intentionally excludes raw/sample databases, generated SQLite templates, Access templates, vendor help files, vendor manuals, and third-party reference documents unless they are explicitly cleared for redistribution and safe for Cowork plugin packaging. The PHDWin output definitions spreadsheet is the only bundled binary reference artifact intended for this public workflow.

Do not commit client PHDWin files, generated SQLite exports, extracted source folders, generated reports, or C# implementation snapshots. The Cowork MCP package runtime is Python.
