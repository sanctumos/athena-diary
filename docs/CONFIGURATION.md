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

Sanctum hosts should keep `DIARY_EMBED_MODE=letta` and reuse the instance’s existing embedding configuration.
