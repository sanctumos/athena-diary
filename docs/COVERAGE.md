# Coverage gate

Contributors: do not merge Build slices that drop package coverage below **90%** line coverage from **unit + e2e** tests.

```bash
pytest --cov=athena_diary_mcp --cov-report=term-missing --cov-fail-under=90
```

CI enforces the same `--cov-fail-under=90` threshold.
