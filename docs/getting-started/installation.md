# Installation

## Requirements

- **Python 3.12 or newer.**
- **[`uv`](https://github.com/astral-sh/uv)** on your `PATH`. `pwnv` shells out to
  it to build the CTF environment and per-challenge environments. Without it,
  `pwnv init` stops before creating anything.

## From PyPI

```bash
pip install pwnv
```

Or, to keep it off your system Python:

```bash
uv tool install pwnv
```

## From source

```bash
git clone https://github.com/CarixoHD/pwnv
cd pwnv
uv sync
```

`uv sync` installs the development dependencies too. See
[Contributing](../dev/index.md) if you intend to change something.

## Verifying the install

```bash
pwnv --help
pwnv doctor
```

`pwnv doctor` is the more useful of the two once a workspace exists: it checks
the configuration, the paths it points at, the tools `pwnv` expects to find, the
CTF environment, and whether the records still match what is on disk.

## Shell integration

`cd` can only happen inside your own shell, so the directory-changing part of
`pwnv` ships as a shell function rather than a command. Add it to your rc file:

=== "bash / zsh"

    ```bash
    eval "$(pwnv shell-init)"
    ```

=== "fish"

    ```fish
    pwnv shell-init | source
    ```

That defines `pwncd`. See [Navigation](../guide/navigation.md).

## Devcontainer

The repository ships a devcontainer that keeps all `pwnv` state inside the
workspace under `.pwnv/`. Opening the folder in a devcontainer-aware editor
builds the image and runs `.devcontainer/post-create.sh`, which installs the
system tooling `pwntools` expects (`binutils`, `gdb`, `patchelf`), syncs the
development environment with `uv sync --locked`, and bootstraps a CTF workspace.

Set `PWNV_SKIP_CTF_INIT=1` before the container is created to skip the CTF
environment bootstrap, which otherwise downloads `angr` and friends on first
build.
