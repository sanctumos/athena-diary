# athena-diary

**SanctumOS · Athena**

Off-context **diary** for Letta agents: SQLite source of truth + MCP tools so journaling does not stuff core memory. Pattern matches [origin_conversation](https://github.com/sanctumos/origin_conversation) (DB + MCP wrapper).

**Status:** Scaffold (v0.1.0) — schema, write/search, embeddings (`sqlite-vec`), and sleeptime clerk land in later Build slices. Product requirements: DSC Tasks [Doc #1039](https://tasks.decisionsciencecorp.com/admin/doc.php?id=1039) (board **Athena Diary**).

---

## What this is (v1 direction)

- **Diary outside the context window** — write freely; retrieve via MCP.
- **Embed summaries** (not full bodies) with **`sqlite-vec`** in the same SQLite file; FTS fallback.
- **Default embed path:** Sanctum / Letta vectorization lanes; optional external provider for standalone.
- **Sleeptime clerk** tags / lesson-family / re-embeds (turn-based).
- **Sensitive material** stays in Broca human blocks (instructional), not the diary.

Sequencing: **ship diary first**; core compaction later so brain surgery has somewhere to put what matters.

---

## Quick start (scaffold)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
# Later slices: pip install -e '.[dev,mcp,vec]'

athena-diary-mcp --version
athena-diary-mcp --describe
athena-diary-mcp health

# Coverage gate (Build slices require ≥90%)
pytest --cov=athena_diary_mcp --cov-report=term-missing --cov-fail-under=90
```

Copy `.env.example` → `.env` when configuring embed/DB paths (later slices).

---

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/OVERVIEW.md](docs/OVERVIEW.md) | Scope and architecture pointer |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Env knobs (embed modes, DB path) |
| [docs/COVERAGE.md](docs/COVERAGE.md) | 90% unit/e2e gate between Build slices |

---

## License

- **Source:** [AGPL-3.0](LICENSE)
- **Docs / non-code:** [CC-BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt)

See [NOTICE](NOTICE).
