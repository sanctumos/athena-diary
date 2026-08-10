# Bootstrapping Athena Diary on a legacy Letta instance

This is how Sanctum attached **Athena Diary** to a long-running self-hosted Letta stack (Athena + sleeptime on the agent host). Use it as a template for any comparable Letta deploy. Paths below are **patterns** — substitute your agent home, venv, and DB location. Do **not** commit real `DIARY_DB` contents, API keys, or core-memory backups into this repository.

---

## What “legacy Letta” means here

| Item | Sanctum pattern |
|------|-----------------|
| Runtime | Self-hosted Letta HTTP API (ADE / API on the agent host) |
| Agents | Hot agent + **sleeptime** companion (`agent_type: sleeptime_agent`) |
| MCP | Letta MCP server registry (stdio servers Letta spawns) |
| Embeddings | Prefer `DIARY_EMBED_MODE=letta` so diary shares the host embed stack |
| Clerk | Sleeptime agent calls `diary_sleeptime_pass` (not cron) |

The product is named after Athena (user #1 of this pattern). The same bootstrap works for **any** Letta agent with its own diary DB.

---

## 1. Install on the agent host

Clone beside the agent tree (example layout):

```text
~/sanctum/agents/<agent>/diary/     # this repo
~/sanctum/agents/<agent>/diary/.venv/
~/sanctum/agents/<agent>/diary/db/  # DIARY_DB lives here (not in git)
```

```bash
cd ~/sanctum/agents/<agent>/diary
git clone https://github.com/sanctumos/athena-diary.git .
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]'
# optional KNN:
.venv/bin/pip install -e '.[vec]'
```

**Letta stdio note:** this package pins **`mcp>=1.10.1,<2`**. Letta’s stdio MCP client expects the 1.x server API. Do not “upgrade” to mcp 2.x on a Letta host without verifying Letta compatibility.

Smoke:

```bash
.venv/bin/athena-diary-mcp --version
.venv/bin/athena-diary-mcp --describe
.venv/bin/athena-diary-mcp health
```

---

## 2. Configure the diary process env

Letta injects env when it starts the MCP stdio child. Minimum:

| Variable | Sanctum value |
|----------|----------------|
| `DIARY_DB` | Absolute path to `…/diary/db/athena-diary.db` |
| `DIARY_EMBED_MODE` | `letta` on Sanctum hosts |

For standalone / non-Letta embed stacks use `external` + `DIARY_EMBED_*` (see [CONFIGURATION.md](CONFIGURATION.md)). Never commit `.env` with secrets.

The SQLite file is created and migrated on first connect. Keep it **outside** git (`*.db` is gitignored).

---

## 3. Register the MCP server in Letta

Register a stdio MCP server named e.g. **`athena_diary`** (name is local to your Letta instance):

| Field | Value |
|-------|--------|
| **type** | `stdio` |
| **command** | `/path/to/diary/.venv/bin/athena-diary-mcp` |
| **args** | `["serve"]` |
| **env** | `DIARY_DB`, `DIARY_EMBED_MODE` (+ host embed secrets if required) |

Equivalent shape:

```json
{
  "server_name": "athena_diary",
  "type": "stdio",
  "command": "/path/to/diary/.venv/bin/athena-diary-mcp",
  "args": ["serve"],
  "env": {
    "DIARY_DB": "/path/to/diary/db/athena-diary.db",
    "DIARY_EMBED_MODE": "letta"
  }
}
```

Use the Letta ADE **MCP servers** UI, or your instance’s `POST /v1/tools/mcp/servers` (or current equivalent) API. Exact routes vary by Letta version — the fields above are what matter.

---

## 4. Attach tools to hot + sleeptime agents

After the server is registered, attach these tools to **both**:

| Tool | Hot agent | Sleeptime agent |
|------|-----------|-----------------|
| `diary_write` | yes | yes (promote / backfill) |
| `diary_get` | yes | yes |
| `diary_search` | yes | yes |
| `diary_sleeptime_pass` | optional | **required** |

On Sanctum, tools appear as Letta `external_mcp` tools once attached from the `athena_diary` server.

**Sleeptime frequency:** Letta’s sleeptime group runs the companion on a turn cadence (e.g. every N foreground turns). The clerk is that companion calling `diary_sleeptime_pass` — not a host crontab.

---

## 5. Prompt the sleeptime clerk (required for intent)

Tool attach alone is not enough. Letta’s injected sleeptime reminder tells the agent to follow **`memory_persona`**. Sanctum also puts clerk rules in the sleeptime **system** prompt.

Minimum policy to encode (system and/or `memory_persona`):

1. Early each sleeptime turn, call `diary_sleeptime_pass` (limit 10–25) **before** `memory_finish_edits`.
2. Hot agent writes raw entries; sleeptime **clerks** (tags, lesson_family, templated summary, see_also, re-embed).
3. Never paste diary bodies into core memory; core stays ruthless (skinny pointers only).
4. Intimate / medical / human-gated → Broca (or equivalent) **human** block — not the diary.
5. Prefer `continue_loop` tool rules on `diary_sleeptime_pass` / `diary_write` so they do not fight an exit-loop finish tool.

Shared hot+sleeptime tip block can remind: hot `diary_write`s; sleeptime must clerk.

Block **labels** on older Sanctum instances should avoid `/` in names (Letta address-by-label bug). Prefer `system_deep_memory` over `system/deep_memory`.

---

## 6. Prompt the hot agent (routing)

Hot agent needs write/search/get and a short routing rule (often in `system_tool_tips` / memory rules):

- Experiential / lesson narrative → `diary_write`, not expanding core.
- Retrieve with `diary_search` → `diary_get`.
- Sensitive material → human block, not diary.

---

## 7. Verify end-to-end

```bash
# On the agent host, same env Letta uses:
export DIARY_DB=/path/to/diary/db/athena-diary.db
export DIARY_EMBED_MODE=letta
.venv/bin/python -c 'from athena_diary_mcp.server import dispatch_tool; print(dispatch_tool("diary_write", {"body":"bootstrap smoke","summary":"smoke"}))'
.venv/bin/python -c 'from athena_diary_mcp.server import dispatch_tool; print(dispatch_tool("diary_search", {"query":"bootstrap smoke","limit":5}))'
.venv/bin/python -c 'from athena_diary_mcp.server import dispatch_tool; print(dispatch_tool("diary_sleeptime_pass", {"limit":5}))'
```

In ADE: confirm both agents list the four tools; trigger a sleeptime pass (or wait for the group cadence) and confirm `diary_sleeptime_pass` runs without tool errors.

---

## 8. What we deliberately did **not** do

- **No prod diary DB in git** — `*.db` gitignored; only `db/.gitkeep`.
- **No cron clerk as default** — `athena-diary-backlog` exists for manual ops only.
- **No intimate content in the diary** — instructional routing to human blocks.
- **No mcp 2.x** on the Letta stdio path until Letta supports it.

---

## Related docs

- [CONFIGURATION.md](CONFIGURATION.md) — env knobs
- [MCP_CLIENTS.md](MCP_CLIENTS.md) — ChatGPT, Claude Code, Cursor, generic MCP
- [AGENTS.md](AGENTS.md) — agent-facing routing card
- [TOOL_REFERENCE.md](TOOL_REFERENCE.md) — tool contracts
