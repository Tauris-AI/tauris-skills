# Tauris Skills

Claude Cowork, ChatGPT, Grok, and Codex Installation Guide

For new users installing on their own machine, including locked-down / no-admin setups.

This guide installs the Tauris skills and optional local database tooling for petroleum engineering workflows. The lowest-friction install is Claude Cowork skills only. Local PHDWin native-file inspection requires Python and, for `.phz`, `.phd`, and `.mod` source files, the 32-bit Clarion / TopSpeed ODBC driver.

## 1. What you are installing

There are independent pieces. Install only the pieces your AI surface can actually use.

| Piece | What it needs |
| --- | --- |
| Skills | File-copying into a supported skills/context location. No admin, no Python, no drivers. |
| SQLite reference templates | Local files included in the repo. No admin, no Python, no drivers for inspection. |
| PHDWin v2 MCP server | Python plus `fastmcp` and `pyodbc`. Native PHDWin extraction also needs the 32-bit Clarion / TopSpeed ODBC driver. |
| ARIES Access export/review | The bundled Access template and, for direct Access reads/writes, a Windows Access ODBC driver. |

Recommendation: install the skills first and confirm they work. Add the MCP server only if you need local PHDWin inspection, PHDWin-to-Aries review, or live database tooling.

## 2. You do not need `C:\Dev` or any special location

Some examples in the repo show a path like `C:\Dev\tauris-skills`. That is only a placeholder. Nothing requires the `C:\` drive root or a folder named `Dev`.

Put the repo inside your own user profile, for example:

```text
%USERPROFILE%\tauris-skills
```

`%USERPROFILE%` normally expands to `C:\Users\<your-name>`.

Locked-down machine: if you have no admin rights and cannot write to `C:\`, you can still install and use the skills and SQLite templates. Only native PHDWin `.phz` / `.phd` / `.mod` extraction needs an admin-installed Clarion / TopSpeed driver.

## 3. Claude Cowork install

Claude Cowork can load the skill folders directly and can launch the optional local MCP server.

### Step 1 - Put the repo somewhere you can write

Copy or clone the repo to:

```text
%USERPROFILE%\tauris-skills
```

If you are offline, copy the folder by USB or network share.

### Step 2 - Copy skill folders

Copy each whole skill folder, including `SKILL.md`, `references/`, and `scripts/`, into:

```text
%USERPROFILE%\.claude\skills\
```

Recommended skills:

| Repo folder | Copies to |
| --- | --- |
| `areas\aries\skills\aries-core` | `.claude\skills\aries-core\` |
| `areas\aries\skills\aries-ac-economic` | `.claude\skills\aries-ac-economic\` |
| `areas\forecasting\skills\auto-forecasting` | `.claude\skills\auto-forecasting\` |
| `areas\phdwin-v2\skills\phdwin-v2-querying` | `.claude\skills\phdwin-v2-querying\` |
| `areas\petroleum-economics\skills\petroleum-economics-review` | `.claude\skills\petroleum-economics-review\` |

When finished, you should have paths such as:

```text
%USERPROFILE%\.claude\skills\aries-core\SKILL.md
```

### Step 3 - Restart Cowork

Fully quit and reopen Claude Cowork. On startup it scans the skills directory and registers any `SKILL.md` it finds.

### Step 4 - Confirm skills loaded

Ask Cowork:

```text
Use the ARIES core skill. Summarize the standard PHDWin-to-Aries review workflow and the key target tables.
```

If it responds using the skill content, the install worked.

### Optional - PHDWin v2 MCP server

Only install this if you need PHDWin inspection or PHDWin-to-Aries conversion review tools.

Open Command Prompt and check the 32-bit Python environment:

```cmd
py -3.12-32 --version
py -3.12-32 -c "import pyodbc, fastmcp; print('pyodbc', pyodbc.version); print('fastmcp ok')"
py -3.12-32 -c "import pyodbc; [print(d) for d in pyodbc.drivers()]"
```

If `fastmcp` or `pyodbc` is missing:

```cmd
py -3.12-32 -m pip install fastmcp pyodbc
```

In Cowork, open Settings -> Developer -> Edit Config and merge in:

```json
{
  "mcpServers": {
    "phdwin-v2": {
      "command": "py",
      "args": [
        "-3.12-32",
        "C:/Users/<your-name>/tauris-skills/areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/phdwin_mcp_server.py"
      ]
    }
  }
}
```

Use your real repo path and forward slashes. Restart Cowork, then test:

```text
Use the phdwin-v2 MCP server. Run env_check and tell me whether this machine is ready to query native PHDWin v2 files for PHDWin-to-Aries conversion.
```

## 4. ChatGPT install / usage

ChatGPT should not be assumed to run local Windows Python, ODBC drivers, `.phz`, `.phd`, `.mod`, `.accdb`, or local repo scripts directly from your workstation.

Use ChatGPT in one of these modes:

### Prompt-only review

Use this when you only need policy, workflow, mapping, or documentation review.

1. Open ChatGPT.
2. Attach non-confidential skill files or the sanitized SQLite templates.
3. Paste this prompt:

```text
Use the attached Tauris skill material as reference. Do not assume access to local PHDWin, ARIES, ODBC, Python, or filesystem tools unless I attach files or expose a connector. Start by summarizing what files you can actually inspect.
```

Do not upload client PHDWin, ARIES, reserve, economics, or owner data unless that upload has been explicitly approved.

### Remote MCP / app access

Use this when ChatGPT needs live tools or private data access. Put the Tauris MCP server near the data, expose it as a remote MCP server or ChatGPT app, and secure it with authentication. Localhost-only MCP servers are not enough for ChatGPT web access.

For private, on-premises, or firewall-bound servers, use a supported tunnel pattern rather than exposing local ports casually.

## 5. Grok install / usage

Grok has built-in connectors and supports custom MCP connectors.

Use Grok in one of these modes:

### Prompt-only review

1. Open Grok.
2. Attach only non-confidential skill files or sanitized SQLite templates.
3. Tell Grok which workflow to use, for example:

```text
Use the attached Tauris PHDWin-to-Aries skill material as reference. Do not assume live local database access. If a needed file or table is missing, ask for it or explain the local extraction step.
```

### Custom MCP connector

If Grok needs live tools, deploy a Tauris MCP server that Grok can reach, then add it as a custom MCP connector in Grok connectors. The MCP server must be reachable over the public internet, or through a tunnel if it runs locally. Keep client data behind authentication and least-privilege tool scopes.

## 6. Codex install / usage

Use Codex when you want a local coding agent to inspect this repo, run scripts, query SQLite templates, or manage conversion code.

### Repo-local skills

Codex discovers skills from `.agents\skills` locations. For a repo-local install, create:

```text
%USERPROFILE%\tauris-skills\.agents\skills\
```

Then copy or symlink skill folders into it, for example:

```text
%USERPROFILE%\tauris-skills\.agents\skills\phdwin-v2-querying\SKILL.md
%USERPROFILE%\tauris-skills\.agents\skills\aries-core\SKILL.md
```

Start Codex from the repo root:

```cmd
cd %USERPROFILE%\tauris-skills
codex
```

Test:

```text
Use the phdwin-v2-querying skill. Inspect the SQLite template inventory and summarize which PHD_ and MOD_ source tables are represented.
```

### Codex MCP config

Codex stores MCP configuration in `config.toml`. For local PHDWin tooling, configure a stdio MCP server in `~\.codex\config.toml` or a trusted project `.codex\config.toml`:

```toml
[mcp_servers.phdwin-v2]
command = "py"
args = [
  "-3.12-32",
  "C:/Users/<your-name>/tauris-skills/areas/phdwin-v2/mcp-servers/PHDWinv2_MCP/scripts/phdwin_mcp_server.py"
]
```

Then restart Codex and use `/mcp` to confirm the server is available.

### Codex local boundary

Codex can run local scripts only when the workspace and sandbox allow it. Native PHDWin extraction still requires Windows Python that can see the 32-bit Clarion / TopSpeed ODBC driver. SQLite review does not require that driver.

## 7. SQLite templates

The repo includes scrubbed or template SQLite files for no-driver inspection:

| Template | Path |
| --- | --- |
| ARIES Access-template SQLite | `areas\aries\reference\templates\aries_access_template.sqlite` |
| ARIES Access-template SQLite, PHDWin package copy | `areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\reference\templates\aries_access_template.sqlite` |
| ARIES review fixture | `areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\reference\templates\aries_review_template.sqlite` |
| PHDWin review fixture | `areas\phdwin-v2\mcp-servers\PHDWinv2_MCP\reference\templates\phdwin_review_template.sqlite` |

The ARIES Access-template SQLite includes Access query/view objects as SQLite views. When writing a working Access database later, write table rows into a copy of `Aries_Template.accdb`; the native Access queries/views in that template will evaluate from the populated tables.

The PHDWin review fixture has 76 synthetic `PHD_` / `MOD_` source tables. It is not converted client data.

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| Skills do not appear after restart | Confirm `SKILL.md` is directly inside each skill folder and fully restart the AI app. |
| Cannot write to `C:\` | Use `%USERPROFILE%`; your user folder should be writable. |
| Native PHDWin driver not found | Native `.phz` / `.phd` / `.mod` extraction needs the 32-bit Clarion / TopSpeed driver. SQLite review does not. |
| 64-bit vs 32-bit mismatch | A 64-bit Python cannot see a 32-bit ODBC driver. Use `py -3.12-32`. |
| ChatGPT or Grok cannot see localhost | Use remote MCP/app deployment or a supported tunnel. Do not assume local-only MCP works from a cloud chat surface. |
| Codex skill not discovered | Put the skill under `.agents\skills`, restart Codex, and invoke it explicitly by name. |

## 9. Source notes

This guide was updated on June 4, 2026.

- OpenAI ChatGPT / API MCP and connectors docs: `https://developers.openai.com/api/docs/guides/tools-connectors-mcp`
- OpenAI Apps SDK docs: `https://developers.openai.com/apps-sdk`
- OpenAI Codex manual, fetched June 4, 2026: `https://developers.openai.com/codex/codex-manual.md`
- xAI Grok connector docs, last updated May 16, 2026: `https://docs.x.ai/grok/connectors`
