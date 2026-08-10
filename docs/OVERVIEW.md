# Overview — athena-diary

MCP + SQLite **diary** for Athena (and later other Sanctum agents): an off-context journal so the impulse to remember does not fill core memory blocks.

Canonical product decisions live in DSC Tasks **Doc #1039** (Athena Diary board). This repo implements that PRD.

## Architecture (target)

```
Athena / sleeptime / Otto
        │  MCP
        ▼
  athena-diary MCP
        │
        ▼
  SQLite (entries + FTS5 + sqlite-vec on summaries)
```

## Scaffold vs later slices

| Slice | Status |
|-------|--------|
| Repo, CI, ≥90% coverage tooling, `--describe` / `health` | **This release** |
| Schema, write/get, FTS, embeds, sleeptime, full MCP tools | Build board tasks |
| moya attach + cron | Deploy board tasks |
| Core compaction into diary | Later (after diary ships) |

## Related

- [origin_conversation](https://github.com/sanctumos/origin_conversation) — same DB+MCP shape (read-only ChatGPT history)
- Broca per-human blocks — intimate data stays there, not in the diary
