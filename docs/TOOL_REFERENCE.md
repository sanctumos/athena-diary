# Tool reference

The MCP server exposes **four tools** for the off-context diary. Tool names and schemas are also available from:

```bash
athena-diary-mcp --describe
```

---

## `diary_write`

Append a diary entry.

### Description (as seen by the LLM)

> Append a diary entry (body required). Optional summary, sensitivity_note, source, run_id, message_id.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `body` | string | **yes** | — | Full diary text. Must be non-empty after trim. |
| `summary` | string | no | — | Optional hot-path gist. Sleeptime may rewrite via template. |
| `sensitivity_note` | string | no | — | Free-text reminder only—not ACL. Intimate content still belongs in the human block. |
| `source` | string | no | `hot_turn` | Provenance label (e.g. `hot_turn`, `sleeptime_promote`). |
| `run_id` | string | no | — | Optional Letta / host run breadcrumb. |
| `message_id` | string | no | — | Optional message breadcrumb. |

Additional properties: **not allowed**.

### Behavior

- Inserts a row into `entries`; FTS triggers index `body` / `summary`.
- Does **not** require sleeptime before the entry is searchable via FTS.
- Embeds may be filled/refreshed when a summary exists and the embed path runs (sleeptime clerk always re-embeds after templating).

### Example

```json
{
  "body": "Today I caught myself stuffing a whole anecdote into recent_context. Writing it here instead.",
  "summary": "Anecdote belongs in diary not recent_context",
  "source": "hot_turn"
}
```

### Response

JSON object for the created entry (`id`, `body`, `summary`, timestamps, etc.). Cross-refs (`see_also_entry_ids`) appear after sleeptime has processed the entry—call `diary_get` again later if needed.

---

## Cross-references: `see_also` and `lesson_family`

These already exist—no separate “dogear” tool is required.

| Mechanism | What it is |
|-----------|------------|
| **`see_also`** | Entry-to-entry cross-refs. Sleeptime links entries whose **summaries** embed as semantically related. **Stored bidirectionally:** when entry 43 links to entry 35, `diary_get(35)` includes 43 in `see_also_newer_entry_ids` and `diary_get(43)` includes 35 in `see_also_older_entry_ids`. |
| **`lesson_family` / `lesson_family_slug`** | Thematic bucket for entries about the same lesson or topic. Assigned during sleeptime. |

**Canonical rule:** old entries are not edited in place. When a view changes, **write a new entry** (cite the earlier id in the body if helpful). Sleeptime may wire `see_also` so the chain stays visible without sanitizing the original.

---

## `diary_get`

Fetch one entry by id, including the **full body** and cross-reference metadata.

### Description

> Fetch one diary entry by id (full body). Response includes `see_also_entry_ids`, `see_also_older_entry_ids`, `see_also_newer_entry_ids` (bidirectional crosslinks by age), `lesson_family_slug`, and `tags`.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entry_id` | integer | **yes** | Entry primary key from search or write. |

### Behavior

- Returns the full row plus cross-ref metadata. Links are **bidirectional** once sleeptime creates them.
- `see_also_entry_ids` — all related entry ids
- `see_also_older_entry_ids` — related entries written **before** this one (corrections point here from newer entries)
- `see_also_newer_entry_ids` — related entries written **after** this one (canonical originals accumulate back-links here)
- Empty until sleeptime has processed the entry and a related summary matched.
- Errors with a clear message if the id does not exist.

### Example

```json
{ "entry_id": 42 }
```

### Response fields (in addition to body/timestamps)

| Field | Meaning |
|-------|---------|
| `see_also_entry_ids` | All related entry ids |
| `see_also_older_entry_ids` | Related entries older than this one |
| `see_also_newer_entry_ids` | Related entries newer than this one (back-links on canonical originals) |
| `lesson_family_slug` | Thematic group slug, if assigned |
| `tags` | Clerk-assigned tag names |

---

## `diary_search`

Search the diary. Returns **pointers** (ids + summaries + dates), not full bodies by default.

### Description

> Search diary by keyword/semantic over summaries. Returns ids + summaries + dates (not full bodies by default).

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **yes** | — | Free text; sanitized into FTS tokens; also used for vector similarity when embeds exist. |
| `limit` | integer | no | `20` | Max hits (clamped to a sensible minimum of 1). |

### Behavior

- **FTS5** over `body` and `summary`, plus tag-name matches.
- **Vector / KNN** over summary embeddings when `sqlite-vec` (or blob fallback search) is available—merged with FTS so a weak summary cannot silent-hole an entry.
- Each hit includes `id`, `summary`, `created_at`, `source`, `rank` (`fts` / `tag` / `vec`), and `tags`.
- Call `diary_get` when you need the full text.

### Example

```json
{
  "query": "lesson family core memory",
  "limit": 15
}
```

### Response

JSON array of hit objects.

---

## `diary_sleeptime_pass`

Clerk batch for unprocessed entries.

### Description

> Clerk: process up to N unprocessed entries—template summary, tags, lesson_family, re-embed, and **see_also** cross-refs when summaries are semantically related (same thread / recurring pattern / revisiting an earlier entry). Idempotent.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | no | `10` | Max unprocessed entries to handle this pass. |

### Behavior

For each selected entry with `sleeptime_processed_at IS NULL`:

1. Annotate (default offline annotator, or a host-provided hook in advanced setups).
2. Build a **templated summary** (gist + tags + lesson_family).
3. Assign tags and `lesson_family`.
4. Re-embed the summary.
5. Link **`see_also`** to semantically related summaries above a similarity threshold (default cosine **0.6** — thematic siblings, not only near-duplicates). Explicit body refs (`entry 35`, `#35`, `correction to 35`) are linked when present.
6. Stamp `sleeptime_processed_at`.

Idempotent: already-processed rows are not selected again.

### Who should call this

- **Primary:** the agent’s **sleeptime** companion each sleeptime turn.
- **Ops:** manual one-shot via MCP or the `athena-diary-backlog` CLI if an operator explicitly runs it. Cron is **not** part of the default v1 design.

### Example

```json
{ "limit": 25 }
```

### Response

JSON object, e.g. `{ "processed": N, "entry_ids": [...], "skipped_already_done": 0 }`.

---

## `diary_see_also_relink`

Re-scan **already-processed** entries and add missing `see_also` links without re-clerking summaries.

### Description

> Re-scan processed entries and add see_also cross-refs (idempotent). Does not rewrite summaries. Use after lowering the similarity threshold or when older entries were clerked before links existed.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | no | `25` | Max processed entries to re-scan this pass. |
| `min_score` | number | no | `0.6` | Cosine similarity floor for semantic neighbors (0–1). |

### Behavior

For each selected entry with `sleeptime_processed_at` set and a non-empty summary:

1. Parse explicit entry refs in the body (`entry 35`, `#35`, `correction to 35`, …) and link when the target exists.
2. Search semantically similar summaries (and body text fallback) above `min_score`.
3. Insert bidirectional `see_also` rows (`INSERT OR IGNORE` — safe to rerun).

Does **not** change summaries, tags, or `sleeptime_processed_at`.

### Example

```json
{ "limit": 50, "min_score": 0.6 }
```

### Response

JSON object, e.g. `{ "scanned": N, "entry_ids": [...], "links_added": M }`.

---

## Error shape

Domain and runtime failures return a text payload starting with `Error: …` (for example empty `body`, missing `entry_id`). Successful calls return indented JSON.

---

## CLI helpers (non-MCP)

| Command | Purpose |
|---------|---------|
| `athena-diary-mcp --version` | Print package version |
| `athena-diary-mcp --describe` | SMCP-style describe JSON including tools |
| `athena-diary-mcp health` | Health JSON (`status`, `plugin`, `version`) |
| `athena-diary-mcp serve` | MCP stdio (default) or `serve --sse` |
| `athena-diary-backlog` | Optional manual backlog helper (not the default deployed clerk) |
