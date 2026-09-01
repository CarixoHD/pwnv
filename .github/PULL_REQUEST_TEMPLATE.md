## What this changes

<!-- One or two sentences. Link the issue if there is one: Fixes #123. -->

## Why

<!-- What was wrong or missing. Skip if the change is obvious from the title. -->

## Checklist

- [ ] `uv run pytest` passes
- [ ] `uv run ruff check . && uv run ruff format --check .` is clean
- [ ] `uv run mypy pwnv` is clean
- [ ] Docs updated, if the change is user-visible
- [ ] `uv run python scripts/gen_cli_docs.py` re-run, if a command or option changed
