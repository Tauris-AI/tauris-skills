#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PLUGIN_GUIDES = [
    REPO_ROOT / "plugins/claude-cowork/phdwin-v2/INSTALL.md",
    REPO_ROOT / "plugins/claude-cowork/aries/INSTALL.md",
    REPO_ROOT / "plugins/claude-cowork/forecasting/INSTALL.md",
    REPO_ROOT / "plugins/claude-cowork/petroleum-economics/INSTALL.md",
]

CANONICAL_PATHS = [
    "areas/phdwin-v2",
    "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP",
    "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/START_HERE.md",
    "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.example.json",
    "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.with_driver_override.example.json",
    "areas/aries",
    "areas/aries/skills/aries-core",
    "areas/aries/skills/aries-ac-economic",
    "areas/aries/mcp-servers/aries-mcp",
    "areas/aries/mcp-servers/aries-mcp/cowork_config.example.json",
    "areas/forecasting",
    "areas/forecasting/skills/auto-forecasting",
    "areas/forecasting/mcp-servers/forecasting-mcp",
    "areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json",
    "areas/petroleum-economics",
    "areas/petroleum-economics/skills/petroleum-economics-review",
    "areas/petroleum-economics/SME_SETUP_GUIDE.md",
]

COWORK_CONFIGS = [
    REPO_ROOT / "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.example.json",
    REPO_ROOT / "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/cowork_config.with_driver_override.example.json",
    REPO_ROOT / "areas/aries/mcp-servers/aries-mcp/cowork_config.example.json",
    REPO_ROOT / "areas/forecasting/mcp-servers/forecasting-mcp/cowork_config.example.json",
]


def _markdown_paths(text: str) -> set[str]:
    candidates = set()
    for match in re.finditer(r"(areas/[A-Za-z0-9_./-]+)", text):
        value = match.group(1).strip().rstrip(".,)")
        candidates.add(value.replace("\\", "/"))
    return candidates


def test_plugin_guides_exist() -> None:
    for guide in PLUGIN_GUIDES:
        assert guide.exists(), f"missing plugin guide: {guide.relative_to(REPO_ROOT)}"


def test_canonical_paths_exist() -> None:
    for rel_path in CANONICAL_PATHS:
        assert (REPO_ROOT / rel_path).exists(), f"missing canonical path: {rel_path}"


def test_plugin_guide_references_resolve() -> None:
    for guide in PLUGIN_GUIDES:
        text = guide.read_text(encoding="utf-8")
        for rel_path in _markdown_paths(text):
            assert (REPO_ROOT / rel_path).exists(), (
                f"{guide.relative_to(REPO_ROOT)} references missing path: {rel_path}"
            )


def test_cowork_configs_parse() -> None:
    for config_path in COWORK_CONFIGS:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert "mcpServers" in data, f"missing mcpServers in {config_path.relative_to(REPO_ROOT)}"


def test_phdwin_cowork_uses_32_bit_python() -> None:
    data = json.loads(COWORK_CONFIGS[0].read_text(encoding="utf-8"))
    args = data["mcpServers"]["phdwin-v2"]["args"]
    assert "-3.12-32" in args


def main() -> int:
    test_plugin_guides_exist()
    test_canonical_paths_exist()
    test_plugin_guide_references_resolve()
    test_cowork_configs_parse()
    test_phdwin_cowork_uses_32_bit_python()
    print("Plugin integrity tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
