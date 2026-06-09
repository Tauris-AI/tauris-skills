# Local E2E Workspaces

Use this top-level folder for local end-to-end testing across Tauris Skills areas.

Everything under this folder is ignored except README files. This keeps packageable area/plugin folders clean while still giving local tests a stable place for source databases, generated artifacts, logs, screenshots, and AI transcripts.

Recommended layout:

```text
e2e-local/
|-- aries/                 Cleared Aries `.accdb` / `.mdb` samples and Access MCP outputs
|-- phdwin-v2/             PHDWin `.phz`, extracted files, SQLite review DBs, Aries exports
|-- forecasting/           Production/pressure CSVs, profile outputs, charts
`-- petroleum-economics/   Local economics review inputs, prompt transcripts, memos
```

Keep reusable test code and CI-safe fixtures in tracked repo paths such as `scripts/` or `areas/*/mcp-servers/*`. Keep customer data, raw databases, generated SQLite files, Access outputs, CSV exports, charts, and local run logs here.
