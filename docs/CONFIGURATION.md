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
~/sanctum/agents/athena/diary/          # git clone of sanctumos/athena-diary
~/sanctum/agents/athena/diary/db/       # DIARY_DB lives here
~/sanctum/venv/bin/athena-diary-mcp     # after: pip install -e '.[mcp]'
~/sanctum/venv/bin/athena-diary-backlog # cron helper
```

Env for the MCP process (Letta stdio server `env`):

| Variable | Value |
|----------|--------|
| `DIARY_DB` | `/home/rizzn/sanctum/agents/athena/diary/db/athena-diary.db` |
| `DIARY_EMBED_MODE` | `letta` |

Letta MCP server registration uses command `athena-diary-mcp` with args `["serve"]`.

## Cron safety net

When unprocessed backlog exceeds threshold (default 50), process a batch:

```bash
DIARY_DB=/home/rizzn/sanctum/agents/athena/diary/db/athena-diary.db \
DIARY_EMBED_MODE=letta \
/home/rizzn/sanctum/venv/bin/athena-diary-backlog --threshold 50 --batch 25 \
  >> /home/rizzn/logs/athena-diary-backlog.log 2>&1
```

Suggested crontab (every 30 minutes):

```
*/30 * * * * DIARY_DB=/home/rizzn/sanctum/agents/athena/diary/db/athena-diary.db DIARY_EMBED_MODE=letta /home/rizzn/sanctum/venv/bin/athena-diary-backlog --threshold 50 --batch 25 >> /home/rizzn/logs/athena-diary-backlog.log 2>&1
```

