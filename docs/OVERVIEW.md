# Overview — Athena Diary

Athena Diary is an **off-context journal** for long-running agents. It stores entries in SQLite and exposes write / get / search / clerk tools over **MCP**, so journaling does not consume the agent’s context window until something is retrieved.

---

## Naming

**Athena Diary** is named after **Athena**, the first Sanctum agent this pattern was designed for (user #1)—the same way many products are named after an early user or muse.

It is **not** “Athena’s private exclusive diary product.” Operators attach the same module to other Letta agents (or any MCP client) with their own `DIARY_DB` path. Multi-agent *shared* diaries are a later concern; v1 assumes **one diary DB per agent (or per deployment)** you configure.

---

## Problem

Long-running agents tend to over-diarize into **core memory** (`recent_context`, durable indexes, tool tips, and similar blocks). Narrative piles up, descriptions drift, and short-term recall suffers. The urge to remember is healthy; **stuffing first-person narrative into always-loaded core is not**.

---

## Goals

1. **Off-context capture** — entries do not cost core/context tokens until retrieved.
2. **Write freely** — selection pressure belongs on **core**, not on the diary.
3. **Cheap retrieval** — embed **summaries**, not full bodies; return pointers; `diary_get` for the body.
4. **Sleeptime filing** — tags / lesson-family / see-also / re-embed on **turn-based sleeptime** clerk passes.
5. **Zero-leak intimacy (practice)** — sensitive material stays in **Broca human blocks** (or your host’s equivalent), not the diary.
6. **origin_conversation-shaped** — SQLite source of truth + MCP tools agents and operators can call.

### Non-goals (v1)

- Per-human diary vaults or dual open/discreet DBs
- Soft ACL / allowlist retrieval over one mixed intimate store
- Replacing Letta archival entirely
- Auto-promoting diary text into core
- Wall-clock cron as the primary clerk (v1 clerk path is **sleeptime tool calls**; a backlog CLI exists for manual ops only)

---

## Architecture

```
Agent (Letta / Claude / Cursor / …)
        │  MCP tools
        ▼
  athena-diary MCP server   (stdio or SSE)
        │
        ▼
  SQLite DB
    entries (+ FTS5)
    tags / lesson_families / see_also
    summary embeddings (sqlite-vec when installed; blob fallback otherwise)
```

| Layer | Responsibility |
|-------|----------------|
| Hot agent turn | `diary_write` when something worth keeping is noticed; optional draft `summary` |
| Retrieval | `diary_search` → ids + summaries; `diary_get` for full text |
| Sleeptime agent / clerk | `diary_sleeptime_pass` to tag, template-summarize, link near-dupes, re-embed |
| Core memory | Skinny pointers only; **never** paste diary bodies |
| Broca human block | Intimate / medical / human-gated material |

---

## What belongs where

| Kind of content | Surface |
|-----------------|---------|
| Experiential noticing, lessons, first-person journal | **Diary** |
| Reference facts for Letta-native recall | **Archival** (OK) |
| Always-needed identity / rules / active window | **Core** (ruthless) |
| Intimate / medical / human-gated | **Broca human block** (not diary) |

`sensitivity_note` on an entry is an optional free-text reminder for the clerk/agent—it is **not** an access-control field.

---

## Data model (v1)

**`entries`** — `id`, timestamps, `body`, optional `summary`, optional `sensitivity_note`, `source` (e.g. `hot_turn`), optional Letta breadcrumbs (`run_id`, `message_id`), `lesson_family_id`, `sleeptime_processed_at`.

**`tags` / `entry_tags`** — sleeptime-assigned labels.

**`lesson_families`** — stable slugs for “same lesson, different costume.”

**`see_also`** — near-duplicate / related entry links from the clerk.

**`embeddings` (+ optional `sqlite-vec`)** — vectors over **summaries**, with model/provider metadata for re-embed migrations.

Schema is applied via **idempotent migrations** on connect.

---

## Embedding modes

| Mode | When | How |
|------|------|-----|
| `letta` (default) | Sanctum / Letta hosts | Share the host’s existing embed / vectorization lanes |
| `external` | Standalone lab / Cursor-only boxes | OpenAI-compatible `/embeddings` via `DIARY_EMBED_*` env |

See [CONFIGURATION.md](CONFIGURATION.md).

---

## Related projects

- [origin_conversation](https://github.com/sanctumos/origin_conversation) — DB + MCP for canonical ChatGPT export search (read-mostly)
- [Letta](https://www.letta.ai) — agent runtime that loads MCP tools into the tool surface
- Broca / Sanctum human blocks — structural home for intimate material

---

## License note

Docs in this tree are **CC-BY-SA 4.0**; source is **AGPL-3.0**. See the repo [NOTICE](../NOTICE).
