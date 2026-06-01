# Area Releases

Use GitHub Releases for novice-friendly downloads. Publish one release with separate zip assets for each area so users download only the tools they need.

All release assets are published under the MIT License. Each generated zip includes the repository `LICENSE` file.

## Release Assets

For a full release, attach these files:

- `phdwin-v2.zip`: PHDWin v2 MCP server, skills, setup docs, cleared PHDWin/ARIES conversion references, Python conversion-review scripts, and the bundled ARIES Access template.
- `aries.zip`: ARIES skills, setup docs, and the `aries-mcp` Cowork MCP server for local `.accdb` and `.mdb` inspection.
- `petroleum-economics.zip`: system-agnostic petroleum economics review skill and checklist material.

## First Release

Suggested first tag:

```text
v1.0.0
```

Suggested title:

```text
Tauris Skills v1.0.0
```

Suggested release notes:

```text
Initial area release packages.

- phdwin-v2: Python Cowork MCP package for read-only PHDWin v2 inspection, SQLite/CSV review export, and PHDWin-to-ARIES conversion-review artifacts.
- aries: ARIES skills plus Python aries-mcp server for local ARIES Access .accdb/.mdb inspection.
- petroleum-economics: generic economics reasonableness review skill without PHDWin or ARIES-specific runtime dependencies.
```

## Build Zips

Run from the repository root:

```bash
python3 scripts/package_area_releases.py --version v1.0.0
```

The script writes zips to `dist/`.

## Publish

1. Confirm the repo is clean and tests pass.
2. Build the zip files.
3. In GitHub, go to Releases, then Draft a new release.
4. Use tag `v1.0.0` for the combined release, or area-specific tags such as `phdwin-v2-v1.0.0` if publishing one area at a time.
5. Attach the generated zip files from `dist/`.
6. Publish the release.

Do not commit the generated zip files. They are release assets only.
