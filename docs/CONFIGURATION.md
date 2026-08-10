# Configuration

Environment variables control the diary database path, embedding provider, and optional SSE bind. See also [`.env.example`](../.env.example).

---

## Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `DIARY_DB` | `./db/athena-diary.db` | Absolute or relative path to the SQLite file. Created and migrated on first use. |
| `DIARY_EMBED_MODE` | `letta` | `letta` = share Sanctum/Letta embed stack; `external` = separate OpenAI-compatible provider; tests may use a deterministic hash provider. |
| `DIARY_EMBED_BASE_URL` | — | Base URL for external embeddings (no trailing path quirks—implementation appends `/embeddings` as documented in code). |
| `DIARY_EMBED_MODEL` | — | External model name (e.g. `text-embedding-3-small`). |
| `DIARY_EMBED_API_KEY` | — | Bearer/API key for external mode. Prefer env or a local pass file—**never commit**. |
| `MCP_HOST` | `127.0.0.1` | SSE bind host (when using `serve --sse`). |
| `MCP_PORT` | `8000` | SSE bind port. |

Load a dotenv file yourself if your process supervisor does not (Letta stdio `env` blocks are the usual Sanctum path).

---

## Embed modes

### `letta` (default)

Intended for hosts that already run Letta’s embedding / vectorization lanes. The diary MCP process should receive the same credentials / base URLs the Letta instance trusts. Prefer this on Sanctum so you do not invent a second mystery embedder on the critical path.

### `external`

Standalone boxes (lab VPS, Cursor-only laptop) set:

```bash
export DIARY_EMBED_MODE=external
export DIARY_EMBED_BASE_URL=https://api.example.com/v1
export DIARY_EMBED_MODEL=text-embedding-3-small
export DIARY_EMBED_API_KEY=…   # from a secret store, not git
```

### Offline / tests

Unit tests use a deterministic hash embedder so CI needs no network. Production agents should use `letta` or `external`.

---

## Optional dependency: `sqlite-vec`

```bash
pip install -e '.[vec]'
```

When present, summary KNN uses `sqlite-vec` inside the same DB file. Without it, the package keeps blob embeddings and a smaller in-process fallback suitable for dev/small DBs. FTS always remains available.

---

## Transports

### STDIO (default)

```bash
athena-diary-mcp serve
```

JSON-RPC over stdin/stdout. Best for local Letta / Cursor / Claude Desktop subprocess configs.

### SSE (HTTP)

```bash
athena-diary-mcp serve --sse --host 127.0.0.1 --port 8000
```

- **GET** `/sse` — open the SSE stream  
- **POST** under `/messages/` — client messages  

`--allow-external` binds `0.0.0.0`. Only use that behind a private network or authenticated reverse proxy. The diary may contain personal narrative—treat exposure like any other private database.

Override host/port with flags or `MCP_HOST` / `MCP_PORT`.

---

## One DB per agent

v1 assumes a **dedicated SQLite file per agent** (or per deployment you intentionally share). Point each Letta MCP server config at its own `DIARY_DB`.

---

## Sanctum / moya layout (reference deploy)

Example layout when the first production user (Athena) runs on a Sanctum host:

```text
~/sanctum/agents/<agent>/diary/           # git clone of sanctumos/athena-diary
~/sanctum/agents/<agent>/diary/.venv/     # local venv recommended
~/sanctum/agents/<agent>/diary/db/        # DIARY_DB lives here
.venv/bin/athena-diary-mcp                # MCP stdio entry (`serve`)
```

Install:

```bash
cd ~/sanctum/agents/<agent>/diary
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]'
# optional: .venv/bin/pip install -e '.[vec]'
```

Letta MCP server sketch:

- **command:** `/path/to/diary/.venv/bin/athena-diary-mcp`
- **args:** `["serve"]`
- **env:** `DIARY_DB=…/db/athena-diary.db`, `DIARY_EMBED_MODE=letta` (plus any host embed secrets)

Attach tools to both the **hot agent** and its **sleeptime** companion so the clerk path can run.

### Clerk path

v1 clerk path is **sleeptime-only**: the sleeptime agent calls `diary_sleeptime_pass`. Do not treat wall-clock cron as required.

The `athena-diary-backlog` CLI remains available for **manual** ops one-shots; it is not the default deployed design.

---

## Security notes

- Keep `DIARY_DB` on disk with permissions limited to the agent host user.
- Never commit API keys or `.env` files with secrets.
- Prefer loopback SSE; avoid public bind without auth in front.
- Diary is not a vault for intimate material—route that to your human-block / Broca path.
