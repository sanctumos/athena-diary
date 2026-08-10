# Configuration

See `.env.example` for the full list.

| Variable | Default | Meaning |
|----------|---------|---------|
| `DIARY_DB` | `./db/athena-diary.db` | SQLite path (created by later slices) |
| `DIARY_EMBED_MODE` | `letta` | `letta` = share Sanctum/Letta embed stack; `external` = separate provider |
| `DIARY_EMBED_BASE_URL` | — | External OpenAI-compatible embed base (external mode) |
| `DIARY_EMBED_MODEL` | — | External model name |
| `DIARY_EMBED_API_KEY` | — | Prefer env / `~/.ssh` pass file — **never commit** |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8000` | SSE bind (when SSE lands) |

# Deploy / ops notes

## moya (Athena) layout

```
~/sanctum/agents/athena/diary/              # git clone of sanctumos/athena-diary
~/sanctum/agents/athena/diary/.venv/        # local venv (Sanctum shared venv is root-owned)
~/sanctum/agents/athena/diary/db/           # DIARY_DB lives here
.venv/bin/athena-diary-mcp                  # MCP stdio entry (`serve`)
.venv/bin/athena-diary-backlog              # cron helper
```

Install:

```bash
cd ~/sanctum/agents/athena/diary
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp,dev]'
# optional: .venv/bin/pip install -e '.[vec]'
```

Env for the MCP process (Letta stdio server `env`):

| Variable | Value |
|----------|--------|
| `DIARY_DB` | `/home/rizzn/sanctum/agents/athena/diary/db/athena-diary.db` |
| `DIARY_EMBED_MODE` | `letta` |

Letta MCP server: command `.venv/bin/athena-diary-mcp`, args `["serve"]`. Attach tools to **Athena_Vernal** and **Athena_Vernal-sleeptime**.

## Cron safety net — **not used (out of spec)**

v1 clerk path is **sleeptime-only** (`diary_sleeptime_pass` on Athena sleeptime turns). Do **not** install a moya crontab for `athena-diary-backlog`.

The `athena-diary-backlog` CLI remains in the package for manual/ops one-shots if Mark explicitly asks; it is **not** part of the deployed diary design.

