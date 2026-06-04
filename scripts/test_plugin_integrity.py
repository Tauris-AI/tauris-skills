#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
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
    "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/aries_review_template.sqlite",
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

CLAUDE_PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin/plugin.json"
CLAUDE_MARKETPLACE = REPO_ROOT / ".claude-plugin/marketplace.json"
AI_PLATFORM_GUIDE = REPO_ROOT / "Tauris_Skills_AI_Platform_Install_Guide.md"


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


def test_claude_plugin_manifest_exists() -> None:
    data = json.loads(CLAUDE_PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    assert data["name"] == "tauris-skills"
    assert data["version"]
    assert data["guides"]


def test_claude_marketplace_plugin_sources_resolve() -> None:
    marketplace = json.loads(CLAUDE_MARKETPLACE.read_text(encoding="utf-8"))
    assert marketplace["name"] == "tauris-skills"
    plugins = marketplace["plugins"]
    assert {plugin["name"] for plugin in plugins} == {
        "phdwin-v2",
        "aries",
        "forecasting",
        "petroleum-economics",
    }
    for plugin in plugins:
        source = plugin["source"]
        assert source.startswith("./"), f"source must be relative to marketplace root: {source}"
        plugin_root = REPO_ROOT / source[2:]
        assert plugin_root.exists(), f"missing plugin source root: {source}"
        manifest = plugin_root / ".claude-plugin/plugin.json"
        assert manifest.exists(), f"missing plugin manifest: {manifest.relative_to(REPO_ROOT)}"
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert manifest_data["name"] == plugin["name"]
        if plugin["name"] in {"phdwin-v2", "aries", "forecasting"}:
            mcp_config = plugin_root / ".mcp.json"
            assert mcp_config.exists(), f"missing plugin MCP config: {mcp_config.relative_to(REPO_ROOT)}"
            mcp_data = json.loads(mcp_config.read_text(encoding="utf-8"))
            assert "mcpServers" in mcp_data


def test_ai_platform_guide_covers_supported_surfaces() -> None:
    text = AI_PLATFORM_GUIDE.read_text(encoding="utf-8")
    required_sections = [
        "## 3. Claude Cowork install",
        "## 4. ChatGPT install / usage",
        "## 5. Grok install / usage",
        "## 6. Codex install / usage",
    ]
    for section in required_sections:
        assert section in text, f"missing platform guide section: {section}"

    required_phrases = [
        "ChatGPT should not be assumed to run local Windows Python",
        "Remote MCP / app access",
        "Grok has built-in connectors and supports custom MCP connectors",
        "Custom MCP connector",
        "Codex discovers skills from `.agents\\skills` locations",
        "Codex stores MCP configuration in `config.toml`",
        "Native PHDWin extraction still requires Windows Python",
    ]
    for phrase in required_phrases:
        assert phrase in text, f"missing platform guide safety/install language: {phrase}"


def test_sqlite_review_template_opens() -> None:
    template = REPO_ROOT / "areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/reference/templates/aries_review_template.sqlite"
    with sqlite3.connect(template) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        required = {
            "TEMPLATE_METADATA",
            "AC_PROPERTY",
            "AC_OWNERSHIP",
            "AC_FORECAST",
            "AC_PRODUCTION_HISTORY",
            "AC_ECONOMIC",
            "AC_PRICE_DECK",
            "AC_COST",
            "AC_CAPITAL",
            "AC_TAX",
            "AC_GROUP_MEMBER",
        }
        assert required.issubset(tables)
        metadata = dict(connection.execute("SELECT key, value FROM TEMPLATE_METADATA"))
        assert metadata["not_vendor_schema"] == "true"


def main() -> int:
    test_plugin_guides_exist()
    test_canonical_paths_exist()
    test_plugin_guide_references_resolve()
    test_cowork_configs_parse()
    test_phdwin_cowork_uses_32_bit_python()
    test_claude_plugin_manifest_exists()
    test_claude_marketplace_plugin_sources_resolve()
    test_ai_platform_guide_covers_supported_surfaces()
    test_sqlite_review_template_opens()
    print("Plugin integrity tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
