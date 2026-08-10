# For agents (Athena, Ada, and others)

**Athena Diary** is an MCP server that gives you an **off-context journal** in SQLite. The product is **named after Athena** (Sanctum’s first long-running agent)—not reserved to her. If these tools are attached to you, they talk to **your** configured `DIARY_DB`.

## Tools

| Tool | Use when |
|------|----------|
| `diary_write` | You have experiential noticing, a lesson, or narrative worth keeping **out of core**. |
| `diary_search` | You need pointers (ids + summaries) related to a query. |
| `diary_get` | You need the **full body** for a known `entry_id`. |
| `diary_sleeptime_pass` | You are the **sleeptime** clerk: tag, summarize, link near-dupes, re-embed a batch. |

Parameters and examples: [TOOL_REFERENCE.md](TOOL_REFERENCE.md).

## Routing rules

1. **Diary** — first-person lessons, anecdotes, “I noticed…”, ongoing themes you may want later.
2. **Core** — ruthless and short. Skinny pointers only (e.g. a lesson-family name → search). **Never** paste diary bodies into core.
3. **Archival** — fine for reference facts that belong in Letta-native recall.
4. **Human / Broca block** — intimate, medical, or human-gated material. **Not** the diary.

`sensitivity_note` is a reminder field, not a lock.

## How the server is run

- **STDIO (usual):** host spawns `athena-diary-mcp serve`.
- **SSE:** host runs `athena-diary-mcp serve --sse`; you still see the same tools.

Operators set `DIARY_DB` and embed mode (`letta` or `external`). You do not need those values to use the tools once they appear.

## Sleeptime

If you are the sleeptime companion, call `diary_sleeptime_pass` each sleeptime turn (reasonable `limit`, e.g. 10–25). The pass is idempotent.

## More detail

- [OVERVIEW.md](OVERVIEW.md) — why this exists
- [GETTING_STARTED.md](GETTING_STARTED.md) — install path for operators
- [MCP_CLIENTS.md](MCP_CLIENTS.md) — how hosts attach the server
- Repo root: [README.md](../README.md)
