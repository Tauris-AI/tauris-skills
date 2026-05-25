# Tauris Skills Planning

This document tracks the work needed to turn `tauris-skills` into a public, installable source for Codex, Claude, ChatGPT, GitHub Copilot, and adjacent agent tools.

## Goals

- Provide curated petroleum engineering skills that are useful to cloud-based LLM agents.
- Keep public content safe: no secrets, raw production exports, customer confidential data, or connection strings.
- Make skills installable or usable from multiple agent surfaces without duplicating domain knowledge by hand.
- Build deterministic validators for fragile workflows where prose instructions are not enough.

## Distribution Targets

| Target | Initial Strategy | Notes |
| --- | --- | --- |
| Codex | Maintain a Codex plugin wrapper under `plugins/tauris-petroleum/` plus `marketplace.json`. | Public GitHub hosting makes the marketplace easier to consume and share. |
| Claude / Claude Code / Claude CoWork | Keep skill folders compatible with the `SKILL.md` plus `references/`, `scripts/`, and `assets/` pattern. | Claude Code supports registering plugin marketplaces and installing plugin bundles. Verify exact Claude CoWork install flow before publishing instructions. |
| ChatGPT / OpenAI | Track OpenAI Skills, Apps SDK, MCP, and connector paths separately. | ChatGPT extension work may require an Apps SDK or MCP surface rather than only static skill files. |
| GitHub Copilot | Maintain `.github/copilot-instructions.md`, `.github/prompts/`, and later `.github/instructions/` or `.github/agents/` as needed. | VS Code Copilot discovers repo customizations from `.github` locations. |

## Feature Backlog

### Repository And Marketplace Packaging

- [x] Initialize the repository and push it to GitHub.
- [x] Publish the repository publicly for marketplace consumption.
- [x] Add a repo-level safety policy for public content.
- [x] Add a Codex plugin wrapper and marketplace manifest.
- [ ] Add installation instructions for Codex.
- [ ] Add installation instructions for Claude Code and Claude CoWork after verifying the current install command.
- [ ] Add installation instructions for Copilot custom instructions and prompt files.
- [ ] Decide whether ChatGPT support should be static skills, an MCP connector, an Apps SDK app, or more than one surface.
- [ ] Add a release/versioning process for marketplace consumers.
- [ ] Add repository topics and a concise GitHub description.

### Skill Architecture

- [x] Create the initial skill folder structure.
- [x] Split ARIES into `aries-core` and `aries-ac-economic` instead of one broad ARIES skill.
- [ ] Create a skill index that explains when to use each skill.
- [ ] Add a curation checklist for new skill proposals.
- [ ] Add a repeatable process for promoting draft notes into verified references.
- [ ] Decide how to mirror or generate plugin-local skill copies from canonical `skills/`.
- [ ] Add tests that verify every skill has valid frontmatter and referenced files exist.

### ARIES Skills

- [ ] Build the ARIES skill roadmap.
- [ ] Curate shared ARIES terminology and module boundaries in `aries-core`.
- [ ] Curate `AC_ECONOMIC` line format documentation from sanitized examples.
- [ ] Implement a real `AC_ECONOMIC` parser after field order and delimiters are verified.
- [ ] Implement `AC_ECONOMIC` rendering with round-trip tests.
- [ ] Add validation rules for required fields, date formats, numeric precision, and allowed code values.
- [ ] Add dry-run mutation templates for ARIES table updates.
- [ ] Identify the next ARIES skills beyond `AC_ECONOMIC`, such as price decks, forecasts, ownership, reserves, imports, and exports.

### PhdWIN Skills

- [ ] Curate sanitized schema landmarks for common PhdWIN databases.
- [ ] Add read-only query templates for common petroleum engineering questions.
- [ ] Add query review guidance for joins, units, date ranges, and assumptions.
- [ ] Add rules for connection handling without storing credentials.
- [ ] Add fixture schemas or synthetic sample data for validating generated SQL.

### Petroleum Economics Skills

- [ ] Expand the economics review checklist.
- [ ] Add reusable review output formats.
- [ ] Add skill guidance for price deck review.
- [ ] Add skill guidance for forecast and decline sanity checks.
- [ ] Add skill guidance for ownership and NRI/WI validation.
- [ ] Add skill guidance for comparing ARIES, PhdWIN, and source spreadsheet outputs.

### Validation And Quality

- [ ] Add a CI workflow for JSON, Markdown, Python, and skill-frontmatter checks.
- [ ] Add tests for skill trigger descriptions.
- [ ] Add sample prompts and expected behavior snapshots.
- [ ] Add deterministic validators for table-line and SQL generation workflows.
- [ ] Add a public-content scan to catch likely secrets before release.
- [ ] Add an evaluation harness for recurring skill tasks.

### Public Documentation

- [ ] Add a public `README.md` section explaining what is installable today.
- [ ] Add a public safety statement explaining what the repo intentionally does not contain.
- [ ] Add contribution guidance for sanitized examples.
- [ ] Add a glossary for petroleum engineering and application-specific terms.
- [ ] Add a compatibility matrix for Codex, Claude, ChatGPT, and Copilot.

## Near-Term Sequence

1. Add installation docs for Codex and Claude Code using the public GitHub repository.
2. Build the ARIES skill roadmap and identify the next 5 ARIES subskills.
3. Curate sanitized `AC_ECONOMIC` examples and convert them into parser tests.
4. Add CI checks for public safety and skill validity.
5. Decide the ChatGPT surface: static skills, MCP connector, Apps SDK app, or a staged combination.

## Open Questions

- What exact Claude CoWork marketplace installation flow should we support?
- Should `skills/` remain canonical with plugin-local copies generated, or should plugin skills be the canonical source?
- Which ARIES database or export formats are safe and useful enough to document publicly?
- Do we want a separate private companion repository for sensitive internal schemas, examples, and live database instructions?
- Should PhdWIN database querying be limited to read-only guidance in the public repo, with write workflows kept private?
