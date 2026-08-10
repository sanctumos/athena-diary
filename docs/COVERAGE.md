# Coverage gate

DSC Tasks **Athena Diary** Build slices: do not start the next Build card until this package reports **≥90%** line coverage from **unit + e2e** tests.

```bash
pytest --cov=athena_diary_mcp --cov-report=term-missing --cov-fail-under=90
```

CI runs the same fail-under threshold. Comment the coverage summary + commit SHA on the finishing Tasks card.
