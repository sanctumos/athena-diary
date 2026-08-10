# Documentation index

Documentation for **Athena Diary**: an off-context SQLite journal exposed to agents through MCP.

> The product is named after **Athena** (Sanctum’s first agent / user #1 of this pattern). It is **not** limited to Athena—any agent host that speaks MCP can run an instance.

| Document | Audience | Contents |
|----------|----------|----------|
| [OVERVIEW.md](OVERVIEW.md) | Everyone | Why diary exists, naming, architecture, routing vs core / Broca / archival |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Users / operators | Install, configure DB + embeds, run MCP, verify tools |
| [TOOL_REFERENCE.md](TOOL_REFERENCE.md) | Users / developers | Full contracts for `diary_write`, `diary_get`, `diary_search`, `diary_sleeptime_pass` |
| [CONFIGURATION.md](CONFIGURATION.md) | Operators | Env vars, embed modes, STDIO vs SSE, Sanctum layout notes |
| [MCP_CLIENTS.md](MCP_CLIENTS.md) | Users | Claude Desktop, Cursor, Letta, generic MCP wiring |
| [AGENTS.md](AGENTS.md) | Agents (Athena, Ada, others) | Short tool summary and routing rules |
| [COVERAGE.md](COVERAGE.md) | Contributors | ≥90% unit/e2e coverage gate |

Repo root: [README.md](../README.md) · [LICENSE](../LICENSE) · [NOTICE](../NOTICE).

Related SanctumOS module: [origin_conversation](https://github.com/sanctumos/origin_conversation) (same DB + MCP shape; read-mostly ChatGPT history).
