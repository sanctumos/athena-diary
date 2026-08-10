# Athena Diary

**SanctumOS**

Off-context **diary** for Letta (and other MCP) agents: a SQLite journal plus MCP tools so the urge to remember does not stuff narrative into core memory.

> **Name:** *Athena Diary* is named after **Athena**, Sanctum’s first long-running agent (user #1 of this pattern)—not because the product is Athena-only. Any Letta agent (or MCP client) can run its own diary instance.

---

## What this is

Agents over-journal into core memory blocks. On a large context window that burns budget and crowds out short-term recall. The impulse to write is good; **core is the wrong surface**.

Athena Diary gives the agent a **rest bucket outside the context window**:

- **Write freely** — volume belongs in the diary, not in core.
- **Retrieve on demand** — search returns pointers (ids + summaries); load full bodies only when needed.
- **Embed summaries** — vector search over gists (`sqlite-vec` when available), with **FTS** on body/summary so a bad summary cannot hide an entry.
- **Sleeptime clerk** — tags, lesson-family, templated summaries, and re-embeds run on turn-based sleeptime passes (not a wall-clock “night”).
- **Sensitive material stays out** — intimate / medical / human-gated content belongs in Broca (or your equivalent) human blocks, not the diary. Privacy in v1 is **instructional** (same discipline as human-block practice), not ACL theater.

Same architectural shape as [origin_conversation](https://github.com/sanctumos/origin_conversation): **SQLite source of truth + MCP wrapper**.

Full product story: **[docs/OVERVIEW.md](docs/OVERVIEW.md)**.

---

## Tools (MCP)

| Tool | Role |
|------|------|
| `diary_write` | Append an entry (body required; optional summary / metadata) |
| `diary_get` | Fetch one entry by id (full body) |
| `diary_search` | Keyword / semantic search over summaries (pointers, not bodies) |
| `diary_sleeptime_pass` | Clerk batch: tag, summarize, link near-dupes, re-embed |

Full API: **[docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md)**.

---

## Quick start

```bash
git clone https://github.com/sanctumos/athena-diary.git
cd athena-diary
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e '.[mcp,dev]'
# Optional vector extension:
# pip install -e '.[vec]'

cp .env.example .env   # set DIARY_DB / embed mode as needed

athena-diary-mcp --version
athena-diary-mcp --describe
athena-diary-mcp health

# MCP stdio (what Letta / Cursor usually spawn):
athena-diary-mcp serve
```

Wire the server into your MCP client: **[docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md)**.  
Step-by-step install: **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)**.

---

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | Purpose, naming, architecture, what belongs where |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Install, first entry, attach to an agent |
| [docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md) | Full MCP tool contracts and examples |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Env vars, embed modes, DB path, transports |
| [docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md) | Claude Desktop, Cursor, Letta, generic MCP |
| [docs/AGENTS.md](docs/AGENTS.md) | Short summary for agent / AI readers |
| [docs/COVERAGE.md](docs/COVERAGE.md) | ≥90% coverage gate for contributors |

---

## Design principles (v1)

1. **Diary first, core ruthlessly thin** — never paste diary bodies into core; core may hold skinny pointers (e.g. lesson-family → search).
2. **No write gates** — clerk cost is controlled by batched sleeptime, not by blocking capture.
3. **Summaries for vectors; FTS for safety** — search remains useful even when summaries drift.
4. **One mixed diary store** — per-human vaults and dual “discreet” DBs are deferred (leak / ops risk).
5. **Complements Letta archival** — experiential / first-person noticing → diary; reference facts may still use archival.

Out of scope for v1: multi-tenant vaults, soft ACL over intimate text, auto-promotion into core, replacing archival entirely.

---

## License

- **Source code:** [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE)
- **Documentation and non-code:** [Creative Commons Attribution-ShareAlike 4.0 International (CC-BY-SA 4.0)](LICENSES/CC-BY-SA-4.0.txt)

See [NOTICE](NOTICE) and [LICENSES/README.md](LICENSES/README.md).
