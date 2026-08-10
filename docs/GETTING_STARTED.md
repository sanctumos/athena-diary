# Getting started

End-to-end path from a fresh clone to an MCP client that can write and search a diary.

Athena Diary is named after Sanctum’s first agent (**Athena**); you can attach the same package to **any** agent by pointing `DIARY_DB` at that agent’s database file.

---

## Prerequisites

- **Python 3.10+**
- An MCP-capable host (Letta, Cursor, Claude Desktop, or another MCP client)
- Optional: `sqlite-vec` (`pip install -e '.[vec]'`) for KNN over summary embeddings
- Optional: an OpenAI-compatible embeddings endpoint if you are not on a Letta host (`DIARY_EMBED_MODE=external`)

---

## Step 1: Install

```bash
git clone https://github.com/sanctumos/athena-diary.git
cd athena-diary
python3 -m venv .venv
# Windows:
# .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e '.[mcp,dev]'
# Recommended for production-like search:
pip install -e '.[vec]'
```

Smoke:

```bash
athena-diary-mcp --version
athena-diary-mcp --describe
athena-diary-mcp health
```

---

## Step 2: Configure the database and embeds

Copy the example env file:

```bash
cp .env.example .env
```

Minimum useful settings:

| Variable | Example | Notes |
|----------|---------|--------|
| `DIARY_DB` | `./db/athena-diary.db` | Created/migrated on first connect |
| `DIARY_EMBED_MODE` | `letta` or `external` | Default `letta` on Sanctum hosts |
| `DIARY_EMBED_BASE_URL` / `DIARY_EMBED_MODEL` / `DIARY_EMBED_API_KEY` | — | Required only for `external` |

For a **second agent**, use a **different** `DIARY_DB` path (one journal file per agent is the v1 assumption).

Full knob list: [CONFIGURATION.md](CONFIGURATION.md).

---

## Step 3: Run the MCP server

### STDIO (local clients — usual path)

Your MCP client should spawn:

```bash
athena-diary-mcp serve
# equivalent:
python -m athena_diary_mcp serve
```

You normally do **not** leave this running in a foreground terminal—the client owns the process. Running it once by hand is only to confirm imports succeed (it will wait on stdin).

### SSE (remote / shared host)

```bash
athena-diary-mcp serve --sse --host 127.0.0.1 --port 8000
# Bind all interfaces only if you understand the exposure:
# athena-diary-mcp serve --sse --allow-external
```

Clients connect with **GET** `/sse` and post messages under `/messages/`. Prefer loopback or a private network; do not publish an open diary MCP to the public internet.

---

## Step 4: Attach your MCP client

See [MCP_CLIENTS.md](MCP_CLIENTS.md) for **ChatGPT**, **Claude Code**, Claude Desktop, Cursor, Letta, and other MCP hosts.

Attaching to a self-hosted / legacy Letta hot + sleeptime pair (Sanctum pattern): [LETTA_BOOTSTRAP.md](LETTA_BOOTSTRAP.md).

After attach, the agent should see:

- `diary_write`
- `diary_get`
- `diary_search`
- `diary_sleeptime_pass`

---

## Step 5: First successful loop

1. **Write** (as the agent or via a tool call):

   ```json
   {
     "body": "Noticed that core memory is the wrong place for long lessons; diary is better.",
     "summary": "Core vs diary routing lesson",
     "source": "hot_turn"
   }
   ```

2. **Search**:

   ```json
   { "query": "core memory diary", "limit": 10 }
   ```

   Expect hits with `id`, `summary`, `created_at`—not full bodies.

3. **Get** the entry by `id` from the search hit.

4. **Clerk** (sleeptime agent or manual ops):

   ```json
   { "limit": 10 }
   ```

   on `diary_sleeptime_pass` to tag, template-summarize, link near-dupes, and re-embed unprocessed rows.

---

## Agent instructions (recommended)

Give the hot agent something like:

- Prefer `diary_write` for experiential / lesson content instead of expanding core narrative blocks.
- Use `diary_search` then `diary_get`; do not paste diary bodies into core.
- Route intimate / medical / human-gated content to the human block—not the diary.

Give the sleeptime agent permission (and habit) to call `diary_sleeptime_pass` each sleeptime turn.

Shorter agent-facing card: [AGENTS.md](AGENTS.md).

---

## Tests (contributors)

```bash
pytest --cov=athena_diary_mcp --cov-report=term-missing --cov-fail-under=90
```

See [COVERAGE.md](COVERAGE.md).

---

## Next reading

- [OVERVIEW.md](OVERVIEW.md) — product boundaries
- [TOOL_REFERENCE.md](TOOL_REFERENCE.md) — full parameter contracts
- [CONFIGURATION.md](CONFIGURATION.md) — operators
