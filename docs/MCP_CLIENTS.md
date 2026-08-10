# MCP client integration

How to attach the Athena Diary MCP server so an assistant can call `diary_write`, `diary_get`, `diary_search`, and `diary_sleeptime_pass`.

The package is named after Sanctum’s first agent (**Athena**); configure a **separate** `DIARY_DB` for each agent you attach.

---

## STDIO vs SSE

| Transport | When | How |
|-----------|------|-----|
| **STDIO** | Client and diary on the same machine | Client spawns `athena-diary-mcp serve` (or `python -m athena_diary_mcp serve`) |
| **SSE** | Remote or shared host | You run `athena-diary-mcp serve --sse`; client connects to the SSE URL |

---

## Claude Desktop

Config file locations:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

### STDIO

```json
{
  "mcpServers": {
    "athena-diary": {
      "command": "/path/to/athena-diary/.venv/bin/python",
      "args": ["-m", "athena_diary_mcp", "serve"],
      "env": {
        "DIARY_DB": "/path/to/athena-diary/db/athena-diary.db",
        "DIARY_EMBED_MODE": "external",
        "DIARY_EMBED_BASE_URL": "https://api.example.com/v1",
        "DIARY_EMBED_MODEL": "text-embedding-3-small",
        "DIARY_EMBED_API_KEY": "set-in-local-config-not-git"
      }
    }
  }
}
```

On Windows, point `command` at `.venv\Scripts\python.exe` and use Windows paths in `env`.

Restart Claude Desktop fully after editing.

---

## Cursor

1. Open **Settings → MCP** (label may vary by Cursor version).
2. Add a server:
   - **Command:** venv Python for this repo
   - **Args:** `-m`, `athena_diary_mcp`, `serve`
   - **Env:** `DIARY_DB`, embed knobs as needed

For SSE, add a server using Cursor’s SSE/URL fields pointed at `http://host:port/sse` (confirm against current Cursor MCP docs).

---

## Letta

Add an MCP server to the agent (and usually to its **sleeptime** twin):

- **Command:** `/path/to/athena-diary/.venv/bin/athena-diary-mcp`  
  (or venv `python` with args `["-m", "athena_diary_mcp", "serve"]`)
- **Args:** `["serve"]` when using the console script as `command`
- **Env:** at least `DIARY_DB`; on Sanctum prefer `DIARY_EMBED_MODE=letta` plus whatever secrets the host already uses for embeddings

Once connected, attach/enable the four diary tools on the agent’s tool list. Hot agent needs write/get/search; sleeptime needs **`diary_sleeptime_pass`** (and usually read tools too).

Exact Letta UI / JSON schema varies by version—follow your Letta MCP server docs for stdio vs SSE fields.

---

## Other MCP clients (generic)

Any client that can launch a stdio MCP server:

```text
command: /path/to/.venv/bin/athena-diary-mcp
args:    serve
env:     DIARY_DB=...  DIARY_EMBED_MODE=...
```

Or SSE: run the server yourself, then point the client at the `/sse` endpoint.

Confirm tools with:

```bash
athena-diary-mcp --describe
```

---

## Checklist after wiring

1. Client shows the four diary tools (or describe lists them).
2. `diary_write` creates an id.
3. `diary_search` finds it; `diary_get` returns the body.
4. Sleeptime (or a manual call) can run `diary_sleeptime_pass` without error.

More detail: [GETTING_STARTED.md](GETTING_STARTED.md), [CONFIGURATION.md](CONFIGURATION.md), [TOOL_REFERENCE.md](TOOL_REFERENCE.md).
