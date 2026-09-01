# Contributing to pwnv

Thanks for taking the time. Bug reports, platform quirks, plugins and docs fixes
are all welcome.

## Getting set up

```bash
git clone https://github.com/CarixoHD/pwnv.git
cd pwnv
uv sync
```

`uv sync` creates `.venv` and installs `pwnv` with its development dependencies.
Prefix commands with `uv run`, or activate the environment.

The hooks are worth installing — they run the same checks CI does, plus
`codespell`, `shellcheck`, and a regeneration of the command reference:

```bash
uv run pre-commit install
```

> [!WARNING]
> Do not run `pwnv init` inside the repository — it writes a workspace to the
> current directory. Point `PWNV_CONFIG` at a scratch file when you want to try
> something end to end:
>
> ```bash
> export PWNV_CONFIG=/tmp/pwnv-scratch/config.json
> ```

## Before opening a pull request

```bash
uv run ruff check .
uv run ruff format .
uv run mypy pwnv
uv run pytest
```

CI runs all four, the test suite on Python 3.12, 3.13 and 3.14, a strict
`mkdocs build`, and a wheel build that is installed into a clean environment and
put through [`scripts/smoke.sh`](scripts/smoke.sh). A PR that is green locally is
green there.

If you changed a command or an option, regenerate the reference:

```bash
uv run python scripts/gen_cli_docs.py
```

## Conventions

| Rule | Why |
| :--- | :--- |
| Type hints on everything | `mypy` runs over `pwnv/` with no per-file ignores |
| Import inside command bodies | Startup time is a feature; a command should not pay for modules it does not use |
| `success`/`info`/`warn`/`error` for anything a human reads | They write to stderr, which keeps stdout a clean data channel |
| Only a command's payload on stdout | `pwncd` and `--json` both depend on it |
| Comments explain *why* | The code already says what it does |
| Sphinx-style docstrings | That is what `mkdocstrings` is configured to parse |

## Adding a command

1. Put it in a module under `pwnv/cli/`, exposed as a `typer.Typer` app.
2. Register it in `_build_app()` in [`pwnv/__init__.py`](pwnv/__init__.py).
3. Guard it with the decorators in `pwnv/utils/guards.py`.
4. If it reports records, take `json_output: bool = JSON` from
   `pwnv/cli/options.py` and emit through `pwnv/utils/serialize.py` — do not
   hand-roll a payload shape.
5. Add a test under `tests/`.

## Adding platform support

Platform support comes from [`ctfbridge`](https://github.com/bjornmorten/ctfbridge).
If an event is not detected, the fix usually belongs upstream rather than here.
Work out what the site is actually running first — a custom frontend over a
standard backend is common, and the backend is often already supported:

```bash
curl -s https://ctf.example.org/api/v1/users/me   # rCTF answers {"kind":"badToken",...}
curl -s https://ctf.example.org/api/v1/challenges # CTFd
```

## Tests

The suite is isolated: an autouse fixture points `PWNV_CONFIG` at a temporary
directory, so no test can reach your real workspace. Nothing talks to a live
platform; stub the `ctfbridge` client instead.

```bash
uv run pytest
uv run pytest tests/test_api_and_json.py -k json
```

See [Testing](https://pwnv.readthedocs.io/en/latest/dev/testing/) for the
module-reload ordering rules, which are easy to trip over.

## Reporting a bug

Open an [issue](https://github.com/CarixoHD/pwnv/issues/new/choose) — the
templates ask for what is needed:

- `pwnv doctor` output,
- the exact command you ran,
- what you expected and what happened instead.

Redact flags, tokens and session cookies. For anything security-sensitive, see
[SECURITY.md](SECURITY.md) instead of opening an issue.

## Documentation

Docs live in [`docs/`](docs/) and are built with MkDocs Material.
[`docs/reference/cli.md`](docs/reference/cli.md) is generated from the Typer app
by `scripts/gen_cli_docs.py` — edit the commands, not the file.

```bash
uv run --extra docs mkdocs serve
```

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
