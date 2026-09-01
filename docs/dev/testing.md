# Testing

```bash
uv run pytest
uv run pytest tests/test_api_and_json.py -k json
uv run pytest -x -q
```

CI runs the suite on Python 3.12, 3.13 and 3.14.

## Isolation

An autouse fixture in `tests/conftest.py` points `PWNV_CONFIG` at a temporary
directory and writes a fresh config there, so no test can reach the real
workspace. It then reloads the modules that resolve the config path at import
time, in dependency order:

```python
_RELOADED_MODULES = (
    "pwnv.utils.config",
    "pwnv.utils.plugin",
    "pwnv.utils.remote",
    "pwnv.utils.crud",
    "pwnv.utils.guards",
    "pwnv.core.plugin_manager",
    "pwnv.core.setup",
    "pwnv.core",
)
```

!!! warning "Reload order is not cosmetic"

    `importlib.reload` mutates a module's `__dict__` in place, so a stale
    *function* reference keeps working — its `__globals__` is that same dict. A
    stale *instance* reference does not. `pwnv.core` re-exports the
    `plugin_manager` singleton, which is why it has to be reloaded after the
    submodule; otherwise every `from pwnv.core import plugin_manager` caller
    holds the previous test's manager.

    The same trap applies in production code: resolve singletons inside the
    function that needs them, not in a decorator factory that runs at import.

## Writing CLI tests

```python
from typer.testing import CliRunner
from pwnv import app

result = CliRunner().invoke(app, ["challenge", "info", "--json"])
assert result.exit_code == 0
```

To assert the stdout/stderr split, the runner has to keep them apart:

```python
def _strict_runner() -> CliRunner:
    try:
        return CliRunner(mix_stderr=False)   # click 8.1
    except TypeError:
        return CliRunner()                   # click >= 8.2 splits them already
```

The diagnostics console is built with `Console(stderr=True)`, which resolves
`sys.stderr` on every write rather than capturing it once — so it works under
both `CliRunner` capture and `contextlib.redirect_stdout`.

## Testing the challenge object

`pwnv.api.current()` resolves from the working directory, so `monkeypatch.chdir`
is the whole setup:

```python
def test_it_resolves_the_challenge_you_are_standing_in(monkeypatch):
    from pwnv.api import current

    challenge = _challenge(_ctf("ApiCTF"), "Baby ROP")
    monkeypatch.chdir(challenge.path)

    assert current().name == "Baby ROP"
```

It re-reads the workspace each call, so a test can mutate a record through
`update_challenge` and assert the next `current()` sees it.

## Import cost

`from pwnv import challenge` must not drag in the CLI. That is asserted in a
subprocess, because once `typer` is imported into the test process the check is
meaningless — and it runs from a challenge directory, since importing the name
is what resolves it:

```python
subprocess.run([sys.executable, "-c",
    "import sys; from pwnv import challenge; assert 'typer' not in sys.modules"],
    cwd=challenge.path)
```

`pwnv.utils.config` imports `typer` only in the branch that needs
`typer.get_app_dir`, which is what keeps that assertion true.

## Network

Nothing in the suite talks to a real platform; remote behaviour is tested
against fakes. If you add a test that would make a network call, stub the
`ctfbridge` client instead.

## The smoke test

The suite runs from the source tree with a monkeypatched config, which leaves a
blind spot: it never sees what the installed package actually contains, and it
never runs a real workspace on disk. `scripts/smoke.sh` covers that, driving the
`pwnv` binary through a full lifecycle.

```bash
uv build
uv venv --python 3.13 /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/pwnv-*.whl
PATH="/tmp/verify/bin:$PATH" scripts/smoke.sh
```

It sets `PWNV_CONFIG` to a temporary directory, then:

1. `pwnv init`, and checks the bundled plugins and templates were copied - which
   only works if `[tool.setuptools.package-data]` put them in the wheel.
2. `ctf add`, `challenge add`, `solve`, and asserts on `--json` output.
3. `from pwnv import challenge` from inside the challenge directory.
4. `workspace backup`, then `init` and `restore` as a second machine, checking
   the files arrived and the paths were rebased.

The `Wheel` job in CI runs it against every build, and `release.yml` runs it
against the artifact before publishing.

## Docs

The command reference is generated, not written:

```bash
uv run python scripts/gen_cli_docs.py          # rewrite docs/reference/cli.md
uv run python scripts/gen_cli_docs.py --check  # what CI runs
```

A pre-commit hook regenerates it whenever `pwnv/cli/` changes, so a renamed
option cannot be committed without its documentation. `mkdocs build --strict`
runs in CI too, which turns a broken link or a bad `:::` reference into a
failure.
