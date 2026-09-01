# Contributing

Contributions are welcome — bug reports, platform quirks, plugins, docs fixes.

## Setting up

```bash
git clone https://github.com/CarixoHD/pwnv.git
cd pwnv
uv sync
```

`uv sync` creates `.venv` and installs the project with its development
dependencies. Prefix commands with `uv run`, or activate the environment.

```bash
uv run pre-commit install
```

The hooks run the same checks CI does, plus `codespell`, `shellcheck` and a
regeneration of the [command reference](../reference/cli.md).

!!! warning "Do not run `pwnv init` in the repository"

    It writes a workspace to the current directory. Point `PWNV_CONFIG` at a
    scratch directory when you want to try things end to end:

    ```bash
    export PWNV_CONFIG=/tmp/pwnv-scratch/config.json
    ```

## Before you open a PR

```bash
uv run ruff check .
uv run ruff format .
uv run mypy pwnv
uv run pytest
```

CI runs all four, the suite on Python 3.12, 3.13 and 3.14, a strict `mkdocs
build`, and a wheel that is installed into a clean environment and put through
[`scripts/smoke.sh`](testing.md#the-smoke-test).

If you changed a command or an option, regenerate the reference — a pre-commit
hook does it for you, and CI fails if it is stale:

```bash
uv run python scripts/gen_cli_docs.py
```

## Conventions

- **Type hints everywhere.** `mypy` runs over `pwnv/` with no ignores beyond the
  ones already in `pyproject.toml`.
- **Import inside command bodies.** Startup time is a feature: a Typer command
  imports what it needs when it runs, not at module import. The same applies to
  anything reachable from `from pwnv import challenge`.
- **stdout is data.** Use `success`/`info`/`warn`/`error` from `pwnv.utils.ui`
  for anything a human reads; they write to stderr. Only the command's payload
  goes to stdout.
- **Comments explain why.** The code says what it does. A comment earns its place
  by explaining a decision that is not obvious from reading it.
- **Docstrings in the Sphinx style**, since that is what `mkdocstrings` is
  configured to parse.

## Adding a command

1. Put it in a module under `pwnv/cli/`, as a `typer.Typer` app.
2. Register it in `_build_app()` in [`pwnv/__init__.py`](https://github.com/CarixoHD/pwnv/blob/main/pwnv/__init__.py).
3. Guard it with `@config_exists()` and friends from `pwnv.utils.guards`.
4. If it reports records, accept `json_output: bool = JSON` from
   `pwnv.cli.options` and emit through `pwnv.utils.serialize`.
5. Add a test.

## Adding platform support

Platform support comes from
[`ctfbridge`](https://github.com/bjornmorten/ctfbridge). If an event is not
detected, the fix usually belongs there rather than here — see
[Remote Platforms](../guide/remote.md#when-detection-fails) for how to work out
what a site is running.

## Reporting a bug

Include `pwnv doctor` output, the command you ran, and what happened instead.
Redact flags and tokens. The
[issue templates](https://github.com/CarixoHD/pwnv/issues/new/choose) ask for
exactly that.

Anything security-sensitive goes through
[private vulnerability reporting](https://github.com/CarixoHD/pwnv/security/advisories/new)
instead — see
[SECURITY.md](https://github.com/CarixoHD/pwnv/blob/main/SECURITY.md).
