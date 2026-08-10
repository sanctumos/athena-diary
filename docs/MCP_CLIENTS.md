# Attaching Athena Diary via MCP

Athena Diary is an **MCP server**. Any client that can launch a stdio process (or connect to SSE/HTTP MCP) can expose `diary_write`, `diary_get`, `diary_search`, and `diary_sleeptime_pass` to an assistant or agent.

The product is named after Sanctum’s first agent (**Athena**). Use a **separate `DIARY_DB`** per assistant/agent instance.

Full Letta/Sanctum bootstrap (legacy self-hosted): **[LETTA_BOOTSTRAP.md](LETTA_BOOTSTRAP.md)**.

---

## Transports

| Transport | When | How |
|-----------|------|-----|
| **STDIO** (default) | Client and diary on the same machine | Client spawns `athena-diary-mcp serve` |
| **SSE** | Remote or shared host | You run `athena-diary-mcp serve --sse`; client connects to `/sse` |

```bash
# STDIO (usual)
athena-diary-mcp serve

# SSE (loopback recommended)
athena-diary-mcp serve --sse --host 127.0.0.1 --port 8000
```

Confirm the tool catalog:

```bash
athena-diary-mcp --describe
```

---

## Shared env (all clients)

| Variable | Notes |
|----------|--------|
| `DIARY_DB` | Absolute path to the SQLite file |
| `DIARY_EMBED_MODE` | `letta` on Letta hosts; `external` elsewhere |
| `DIARY_EMBED_BASE_URL` / `MODEL` / `API_KEY` | Required for `external` |

Do not put API keys in committed JSON. Prefer OS env, secret managers, or `${VAR}` expansion where the client supports it.

---

## Claude Desktop

Config file:

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "athena-diary": {
      "command": "/path/to/athena-diary/.venv/bin/athena-diary-mcp",
      "args": ["serve"],
      "env": {
        "DIARY_DB": "/path/to/athena-diary/db/my-assistant-diary.db",
        "DIARY_EMBED_MODE": "external",
        "DIARY_EMBED_BASE_URL": "https://api.example.com/v1",
        "DIARY_EMBED_MODEL": "text-embedding-3-small",
        "DIARY_EMBED_API_KEY": "set-locally-not-in-git"
      }
    }
  }
}
```

Windows: use `.venv\Scripts\athena-diary-mcp.exe` (or `python.exe` + `["-m", "athena_diary_mcp", "serve"]`). Restart Claude Desktop fully after edits.

---

## Claude Code

Claude Code manages MCP via CLI and JSON scopes ([Claude Code MCP docs](https://code.claude.com/docs/en/mcp)).

### CLI (stdio)

```bash
claude mcp add --transport stdio \
  --env DIARY_DB=/path/to/db/my-assistant-diary.db \
  --env DIARY_EMBED_MODE=external \
  --env DIARY_EMBED_BASE_URL=https://api.example.com/v1 \
  --env DIARY_EMBED_MODEL=text-embedding-3-small \
  --env DIARY_EMBED_API_KEY=$DIARY_EMBED_API_KEY \
  athena-diary \
  -- /path/to/athena-diary/.venv/bin/athena-diary-mcp serve
```

Put Claude’s flags **before** the server name; everything after `--` is the server command.

Scopes: `--scope local` (default), `project` (`.mcp.json` in repo), or `user`.

### Project `.mcp.json` sketch

```json
{
  "mcpServers": {
    "athena-diary": {
      "type": "stdio",
      "command": "/path/to/athena-diary/.venv/bin/athena-diary-mcp",
      "args": ["serve"],
      "env": {
        "DIARY_DB": "/path/to/db/my-assistant-diary.db",
        "DIARY_EMBED_MODE": "external",
        "DIARY_EMBED_BASE_URL": "${DIARY_EMBED_BASE_URL}",
        "DIARY_EMBED_MODEL": "${DIARY_EMBED_MODEL}",
        "DIARY_EMBED_API_KEY": "${DIARY_EMBED_API_KEY}"
      }
    }
  }
}
```

Use `${VAR}` so secrets stay out of git. Verify with `/mcp` inside Claude Code.

---

## ChatGPT (OpenAI Connectors + Secure MCP Tunnel)

ChatGPT does **not** typically spawn a random local stdio binary the way Claude Desktop does. For a **private** diary MCP on your machine or VPC, OpenAI’s path is the **[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)** (`tunnel-client`): outbound HTTPS to OpenAI, local forward to your MCP (stdio or HTTP). No inbound firewall hole required.

High-level:

1. Install and run Athena Diary locally (stdio) or as SSE/HTTP on a private URL.
2. Provision a tunnel id + runtime API key in OpenAI platform tunnel settings.
3. Point `tunnel-client` at this server, e.g. stdio:

   ```bash
   tunnel-client init \
     --sample sample_mcp_stdio_local \
     --profile athena-diary \
     --tunnel-id tunnel_YOUR_ID \
     --mcp-command "/path/to/athena-diary/.venv/bin/athena-diary-mcp serve"

   # Ensure DIARY_DB / DIARY_EMBED_* are in the environment for that process
   export DIARY_DB=/path/to/db/my-chatgpt-diary.db
   export DIARY_EMBED_MODE=external
   # …embed knobs…

   tunnel-client doctor --profile athena-diary --explain
   tunnel-client run --profile athena-diary
   ```

4. While the tunnel daemon is healthy, enable/verify the connector under ChatGPT **Settings → Connectors** ([chatgpt.com connectors](https://chatgpt.com/#settings/Connectors)).

Treat the diary DB as personal data: one DB for ChatGPT use, separate from Letta/Claude if you do not intend to share journals across products.

OpenAI’s tunnel UX and flags evolve — follow the current [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) and [tunnel-client](https://github.com/openai/tunnel-client) docs if names differ slightly.

---

## Cursor

1. **Settings → MCP** (label varies by version).
2. Add a server:
   - **Command:** `/path/to/athena-diary/.venv/bin/athena-diary-mcp`
   - **Args:** `serve`
   - **Env:** `DIARY_DB`, embed knobs

Or `python` / `python.exe` with args `-m`, `athena_diary_mcp`, `serve`.

SSE: point Cursor’s URL/SSE fields at `http://127.0.0.1:8000/sse` (or your host) after `serve --sse`.

---

## Letta (self-hosted or Cloud)

See **[LETTA_BOOTSTRAP.md](LETTA_BOOTSTRAP.md)** for the full Sanctum/legacy bootstrap.

Short form:

1. Register stdio MCP server (`athena-diary-mcp` + `serve` + env).
2. Attach all four tools to the hot agent.
3. Attach all four (especially `diary_sleeptime_pass`) to the sleeptime companion.
4. Put clerk instructions in sleeptime **system** + **`memory_persona`** (Letta’s sleeptime reminder points at `memory_persona`).

Pin **`mcp` 1.x** (`<2`) for Letta stdio compatibility.

---

## Other agent frameworks (generic MCP)

Anything that speaks MCP as a **client** can host this server:

| Host class | Typical wiring |
|------------|----------------|
| **Custom LangGraph / LlamaIndex / Autogen tool bridges** | Spawn stdio MCP client library against `athena-diary-mcp serve`, map tools into the framework’s tool list |
| **Continue / Zed / other IDE agents** | Same JSON shape as Claude Desktop when they support MCP stdio |
| **Remote agent runners** | Run `serve --sse` (or a streamable-HTTP proxy in front) on a private network; point the runner at the URL |
| **SMCP / plugin buses** | Optional later: wrap diary CLI behind an SMCP plugin; v1 ships as a **native MCP server**, not an SMCP plugin |

Minimal stdio contract every client needs:

```text
command: /path/to/.venv/bin/athena-diary-mcp
args:    ["serve"]
env:     DIARY_DB=...  DIARY_EMBED_MODE=...
```

SSE contract:

```text
GET  http://HOST:PORT/sse
POST http://HOST:PORT/messages/   (MCP SSE post path)
```

Prefer loopback or private network. Do not publish an unauthenticated diary MCP on the public internet.

---

## Prompting the host assistant (non-Letta)

MCP exposes tools; it does not teach the model *when* to use them. For Claude / ChatGPT / Cursor, add a short system or project instruction, for example:

- Prefer `diary_write` for lasting notes instead of stuffing the chat with “remember this forever” prose.
- Search with `diary_search`, then `diary_get` for full text.
- Do not store intimate / medical / human-gated material in the diary if you have a safer vault.
- If you run a “compaction” or overnight job, call `diary_sleeptime_pass` periodically (Letta sleeptime does this automatically when prompted).

Agent-facing card: [AGENTS.md](AGENTS.md).

---

## Checklist after wiring

1. Client lists the four diary tools (`--describe` matches).
2. `diary_write` returns an `id`.
3. `diary_search` finds it; `diary_get` returns the body.
4. `diary_sleeptime_pass` runs without error (empty backlog is OK).
5. `DIARY_DB` is **not** committed to git.

---

## Related

- [LETTA_BOOTSTRAP.md](LETTA_BOOTSTRAP.md) — Sanctum / legacy Letta attach
- [GETTING_STARTED.md](GETTING_STARTED.md) — install from zero
- [CONFIGURATION.md](CONFIGURATION.md) — env and SSE security
- [TOOL_REFERENCE.md](TOOL_REFERENCE.md) — parameters and behavior
