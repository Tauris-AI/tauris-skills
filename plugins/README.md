# Tauris Plugins

Tool-facing plugin adapters live here.

The canonical skills, MCP servers, references, and scripts stay under `areas/`. Plugin folders should contain install guides, small config examples, and surface-specific instructions only.

## Current Plugin Surfaces

- `claude-cowork/`: Claude Cowork install guides and MCP registration instructions.

Do not copy area code or reference packs into plugin folders. Point installers to the canonical area paths, then build release artifacts from those paths when needed.

Plugin updates should stay neutral and tool-specific: installation steps, required local paths, permissions, and activation prompts.
