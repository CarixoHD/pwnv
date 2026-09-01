# Releasing

Versions come from git tags via `setuptools-scm`; there is no version string to
edit in the source.

```toml
[tool.setuptools_scm]
version_scheme = "post-release"
local_scheme = "no-local-version"
```

## Cutting a release

Notes are drafted as you go: `release-drafter.yml` keeps a draft release on
[the releases page](https://github.com/CarixoHD/pwnv/releases), grouped by the
labels on each merged PR. Read it before tagging - it is the changelog.

```bash
git switch main && git pull
uv run pytest && uv run ruff check . && uv run mypy pwnv
git tag -a v0.4.0 -m "v0.4.0"
git push origin v0.4.0
```

Pushing a `v*.*.*` tag triggers
[`release.yml`](https://github.com/CarixoHD/pwnv/blob/main/.github/workflows/release.yml).
It builds the distributions, checks the metadata, installs the wheel into a
clean environment and runs [`scripts/smoke.sh`](testing.md#the-smoke-test)
against it. Only if that passes does the second job upload to PyPI with the
`PYPI_API_TOKEN` repository secret.

Then publish the draft release for the tag you just pushed.

## Checking the build first

The same check CI runs, locally:

```bash
uv build
uvx twine check dist/*
uv venv --python 3.13 /tmp/verify
uv pip install --python /tmp/verify/bin/python dist/pwnv-*.whl
PATH="/tmp/verify/bin:$PATH" scripts/smoke.sh
```

This is worth doing by hand after any change to `[tool.setuptools.package-data]`
or the bundled examples. A file that is in the repository but not in the wheel
breaks `pwnv init` for everyone installing from PyPI, and nothing else notices.

## Documentation

Read the Docs builds from `.readthedocs.yaml` on every push to `main` and on
tags. The `post_checkout` step matters:

```yaml
post_checkout:
  - git fetch --unshallow || true
  - git fetch --tags || true
```

Read the Docs clones shallowly, and `setuptools-scm` needs the tag history to
work out a version — without those two lines the install step fails.

Build the site locally with:

```bash
uv run --extra docs mkdocs serve
```
