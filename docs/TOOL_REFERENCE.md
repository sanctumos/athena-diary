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

JSON object for the created entry (`id`, `body`, `summary`, timestamps, etc.).

---

## `diary_get`

Fetch one entry by id, including the **full body**.

### Description

> Fetch one diary entry by id (includes full body).

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entry_id` | integer | **yes** | Entry primary key from search or write. |

### Behavior

- Returns the full row as JSON.
- Errors with a clear message if the id does not exist.

### Example

```json
{ "entry_id": 42 }
```

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

> Clerk: process up to N unprocessed diary entries (tags, lesson_family, templated summary, re-embed, see_also). Idempotent.

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
5. Link `see_also` to near-duplicate summaries above a similarity threshold.
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
