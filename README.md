# pwnv: A CTF Workspace Management Tool 🛠️

**pwnv** is a Command-Line Interface (CLI) utility designed to optimize and organize CTF workflows. It facilitates challenge management, environment setup, and integration with remote CTF platforms, providing a structured approach to CTF participation.

-----

## 🎯 Overview

`pwnv` addresses common challenges in CTF participation, such as disorganized challenge files and manual platform interaction. It provides a standardized framework to structure CTF events, automate setup procedures, and interface with platforms like CTFd, enabling participants to concentrate on problem-solving and enhancing overall efficiency.

-----

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🗂️ **Structured Workspace** | Establishes a consistent and organized directory structure for CTFs and their associated challenges. |
| 📦 **Virtual Environments** | Manages isolated Python virtual environments for CTF workspaces, utilizing [`uv`](https://github.com/astral-sh/uv) for rapid setup. |
| 🔄 **Remote Synchronization**| Enables fetching challenges, descriptions, and attachments from CTFd instances using the [`ctfbridge`](https://pypi.org/project/ctfbridge) library. `--watch` polls a live event and reports only what changed. |
| 🚀 **Remote Flag Submission**| Allows direct submission of flags to remote CTF platforms via the command line. |
| 🔌 **Plugin Architecture** | Supports custom Python plugins for automating challenge setup based on predefined categories (e.g., pwn, web). Ships with a working example, installed on `pwnv init`. |
| 🧭 **Fast Navigation** | `pwncd <name>` jumps straight to a challenge directory, with fuzzy selection when you omit the name. |
| 📊 **Progress Overview** | `pwnv status` reports solves and points across the workspace, or per category with what is left to do. |
| 🏷️ **Challenge Tagging** | Provides functionality to tag solved challenges with relevant keywords for efficient searching and retrieval. |
| ✨ **Interactive Interface**| Employs fuzzy finders and interactive prompts for intuitive navigation and user input. |

-----

## 🏗️ Installation Guide

### Prerequisites

  * Python 3.12 or higher.
  * [`uv`](https://github.com/astral-sh/uv): Ensure `uv` is installed and accessible via the system `PATH`.

### Option 1: Via pip

```bash
pip install pwnv
```

### Option 2: From Source (Development)

```bash
git clone https://github.com/CarixoHD/pwnv
cd pwnv
pip install --editable .
```

-----

## 🚀 Quickstart Guide

1.  **Initialize the workspace:**
    ```bash
    pwnv init --ctfs-folder ~/CTFs
    source ~/CTFs/.pwnvenv/bin/activate
    ```
2.  **Add a CTF event:**
    ```bash
    # Add a local event
    pwnv ctf add ExampleCTF_Local

    # Add a remote event (prompts for URL and credentials)
    pwnv ctf add ExampleCTF_Remote
    ```
3.  **Add a challenge:**
    ```bash
    pwnv challenge add RopMaster # Select category when prompted
    ```
4.  **Navigate to the challenge directory and begin work:**
    ```bash
    eval "$(pwnv shell-init)"   # add this line to your shell rc file
    pwncd RopMaster
    # Begin solving the challenge.
    ```
5.  **Mark the challenge as solved:**
    ```bash
    pwnv solve --flag "FLAG{example_flag}"
    # Enter tags when prompted (e.g., "buffer-overflow, ROP").
    ```
6.  **Check where you stand:**
    ```bash
    pwnv status --detail
    ```

-----

## 🧰 Devcontainer

This repo includes a devcontainer configuration that isolates `pwnv` state
inside the workspace. Opening the folder in a devcontainer-aware editor builds
the container and runs [`.devcontainer/post-create.sh`](.devcontainer/post-create.sh),
which:

  * installs the system tooling `pwntools` expects (`binutils`, `gdb`, `patchelf`, ...),
  * syncs the development environment with `uv sync --locked`,
  * installs the Claude Code CLI (devcontainer feature) and the Codex CLI (`@openai/codex`),
  * bootstraps the CTF workspace with `pwnv init --yes --ctfs-folder .pwnv/CTF`.

Config and CTF data stay under `.pwnv/` (already gitignored), and the `.venv`,
uv cache, and agent credentials live in named volumes so they survive rebuilds.
The editor extensions for Claude Code, Codex, Python, Ruff, and mypy are
installed automatically.

Set `PWNV_SKIP_CTF_INIT=1` before the container is created to skip the CTF
environment bootstrap (it downloads `angr` and friends on first build).

-----

## 🧠 Core Concepts

### Workspace Organization

`pwnv` enforces a hierarchical directory structure. A primary CTF folder contains individual CTF event directories, which in turn contain challenges categorized by type:

```
~/CTFs/
├── .pwnvenv/
├── ExampleCTF_Local/
│   ├── pwn/
│   │   └── RopMaster/
│   │       └── solve.py
│   └── web/
│       └── WebChallenge/
└── ExampleCTF_Remote/
    ├── .env
    ├── .session
    ├── crypto/
    │   └── CryptoChallenge/
    └── ...
```

### Remote Platform Integration

Leveraging `ctfbridge`, `pwnv` interacts with remote CTF platforms to:

  * Retrieve challenge data (descriptions, values, categories, tags).
  * Download associated attachments.
  * Handle authentication via credentials or API tokens.
  * Maintain session state.
  * Submit flags programmatically via `pwnv solve`.

### Plugin System

The plugin system allows for the execution of category-specific Python scripts during challenge creation, automating setup tasks like generating boilerplate solver scripts or setting up tools.

-----

## 🧩 Plugin Architecture

`pwnv` features an extensible plugin system that allows users to define custom actions executed automatically during challenge creation (`pwnv challenge add`). This enables the automation of boilerplate setup, tool integration, and other category-specific tasks.

### Plugin Location

  * **Plugin Scripts:** Reside within the `plugins` folder in your `pwnv` configuration directory (typically `~/.config/pwnv/plugins/`). Each `.py` file represents a potential plugin.
  * **Template Files:** Associated template files (e.g., `solve.py` skeletons) are stored in the `templates` folder, organized by category (e.g., `~/.config/pwnv/templates/pwn/`).

`pwnv init` seeds both folders with the examples that ship with `pwnv` (a pwn plugin and a pwntools ROP template) and selects them for their categories, so `pwnv challenge add` produces a working solver script out of the box. They are ordinary files: edit them, or pass `--no-examples` to start empty. Re-running the copy never overwrites a file you have changed, and a category you have already assigned keeps your plugin.

### Plugin Structure

A `pwnv` plugin is a Python class that inherits from `pwnv.plugins.ChallengePlugin`. It must be decorated with `@register_plugin` to be discoverable.

Key components include:

  * **`@register_plugin`:** Decorator that makes the plugin available to `pwnv`.
  * **`category(self) -> Category:`:** Abstract method that must return the `pwnv.models.challenge.Category` for which this plugin should be considered.
  * **`logic(self, challenge: Challenge) -> None:`:** Abstract method containing the core custom logic to be executed.
  * **`templates_to_copy: Dict[str, str | None]`:** A class attribute specifying which files from the `templates` directory should be copied into the new challenge directory.
  * **Template placeholders:** Any `{{placeholder}}` tokens in template files are replaced with challenge metadata. Examples: `{{service.host}}`, `{{service.port}}`, `{{service.url}}`, `{{challenge.name}}`, `{{challenge.points}}`. Missing values keep the placeholder unchanged.

### Example Plugin (`pwn_plugin.py`)

```python
from pwnv.core import register_plugin
from pwnv.models.challenge import Category
from pwnv.plugins.plugin import ChallengePlugin
from pwnv.models import Challenge
from pwnv.utils.ui import info

@register_plugin
class BasicPwnPlugin(ChallengePlugin):
    # Copy 'solve.py' and 'gdbinit' from templates/pwn/ to the challenge dir.
    templates_to_copy = {
        "solve.py": None,
        "gdbinit": "gdbinit_rop" # save as gdbinit_rop
    }

    def category(self) -> Category:
        return Category.pwn

    def logic(self, challenge: Challenge) -> None:
        # Custom logic for pwn challenges
        info(f"Set up basic pwn environment for {challenge.name}")

```

-----

## ⌨️ Command Reference

The following table summarizes the available commands. For detailed usage, append `--help` to any command or subcommand.

| Command | Description |
| :--- | :--- |
| `pwnv init` | Initializes the `pwnv` environment and workspace, seeding it with the bundled example plugins and templates. Use `--python` to choose the interpreter (default 3.13), `--no-install` to skip the default packages, and `--no-examples` to skip the examples. |
| `pwnv reset` | Removes all `pwnv` configurations and CTF data (exercise caution). |
| | |
| `pwnv ctf add <name>` | Adds a new CTF event (local or remote). |
| `pwnv ctf remove` | Deletes a CTF event and its challenges. `--yes` skips the prompt. |
| `pwnv ctf info` | Displays metadata for a selected CTF. |
| `pwnv ctf sync` | Adds and updates challenges from a remote CTF, reporting only what changed. `--watch` polls until the CTF stops. |
| `pwnv ctf start` | Sets a CTF's status to 'running'. |
| `pwnv ctf stop` | Sets a CTF's status to 'stopped'. |
| | |
| `pwnv challenge add <name>`| Adds a new challenge, triggering relevant plugins. |
| `pwnv challenge remove` | Deletes a specific challenge. `--yes` skips the prompt. |
| `pwnv challenge info` | Displays metadata for a selected challenge, including the fetched description, connection string, and attachments. |
| `pwnv challenge filter` | Lists solved challenges based on specified tags. |
| `pwnv challenge search <QUERY>` | Searches names, descriptions, categories, and tags. With only `--ctf` it lists that CTF. |
| `pwnv challenge note add <TEXT>` | Adds a timestamped Markdown note. |
| `pwnv challenge note show` | Displays the current challenge notes. |
| `pwnv challenge env add <PACKAGE...>` | Installs packages in a challenge-local environment. |
| `pwnv challenge env run <COMMAND...>` | Runs a command in the challenge environment. |
| `pwnv challenge scaffold` | Runs a category's plugin and template against an existing challenge. Never overwrites without `--force`. |
| `pwnv challenge path [NAME]` | Prints a challenge directory and nothing else, for `cd "$(...)"`. |
| | |
| `pwnv solve` | Submits the flag and marks the challenge solved. A flag the platform rejects is recorded in the history but leaves the challenge unsolved, and exits non-zero. |
| `pwnv solve --history` | Displays submission history with flags redacted. |
| `pwnv status` | Displays solved and point progress for the workspace. `--detail` adds per-category progress, recent solves, and what is left. |
| `pwnv shell-init` | Prints the shell function that defines `pwncd`. |
| `pwnv doctor` | Checks workspace configuration, paths, tools, the CTF environment, and consistency. |
| | |
| `pwnv plugin add <name>` | Creates a new plugin and its associated template. |
| `pwnv plugin remove` | Deletes an existing plugin file. |
| `pwnv plugin info` | Displays information about registered plugins. |
| `pwnv plugin select` | Assigns a specific plugin to a challenge category. |
| `pwnv workspace backup [PATH]` | Creates a full archive, including challenge files and credentials. |
| `pwnv workspace export [PATH]` | Exports portable workspace metadata without files or credentials. |
| `pwnv workspace import <PATH>` | Merges metadata into the current workspace, rebasing paths. Use `--replace` to discard local metadata instead. |

### Noninteractive usage

Common workflows can be scripted without interactive selectors:

```bash
pwnv ctf add ExampleCTF --local
pwnv ctf add DemoCTF --url https://demo.ctfd.io/ --username user --password password
pwnv ctf sync --ctf DemoCTF
pwnv challenge add RopMaster --ctf ExampleCTF --category pwn
pwnv challenge search rop --ctf ExampleCTF
pwnv challenge search --category pwn --tag rop --min-points 100 --unsolved
pwnv challenge scaffold --challenge RopMaster --ctf ExampleCTF --category pwn --force
pwnv challenge path RopMaster --ctf ExampleCTF
pwnv challenge remove --challenge RopMaster --ctf ExampleCTF --yes
pwnv solve --flag 'FLAG{example}' --challenge RopMaster --tags pwn,rop
pwnv solve --history --challenge RopMaster --ctf ExampleCTF
pwnv status --ctf ExampleCTF --detail --json
pwnv doctor
pwnv workspace backup ./backups/pwnv --force
pwnv workspace import ./pwnv-export.json --force
```

For remote automation, credentials can be passed through `PWNV_CTF_USERNAME`
and `PWNV_CTF_PASSWORD`, or `PWNV_CTF_TOKEN`, instead of command-line options.
Environment variables avoid exposing secrets in shell history and process listings.

Running `pwnv ctf sync` updates existing challenge points, categories, solved state,
descriptions, services, tags, and attachments in addition to fetching new challenges.
Local tags, solved progress, flags, and challenge directory paths are preserved.

### Jumping between challenges

`cd` can only happen in your own shell, so `pwnv` ships a function instead of a
command. Add this to `~/.bashrc`, `~/.zshrc`, or `~/.config/fish/config.fish`:

```bash
eval "$(pwnv shell-init)"
```

`pwncd` then takes you to a challenge directory, or opens a picker with no
argument:

```bash
pwncd baby-rop     # the directory name, as shell completion gives it
pwncd 'Baby ROP'   # or the real name
pwncd              # pick from a list
```

Names collide across events, so a bare name resolves against the CTF you are
standing in first, then running CTFs, and only a genuine tie asks.

### Scaffolding an existing challenge

`pwnv challenge add` runs the plugin for the challenge's own category. Sometimes
you want a different one: a web challenge with a binary attached still deserves
the pwn template.

```bash
pwnv challenge scaffold --category pwn --suffix _pwn
pwnv challenge scaffold --plugin my_pwn_plugin --force
```

This runs the chosen plugin and renders its template; it does not change the
challenge's category or anything else about the record. Existing files are left
alone unless you pass `--force`, and `--suffix` writes `solve_pwn.py` next to a
`solve.py` you are already working in.

### Watching a live CTF

```bash
pwnv ctf sync --ctf DemoCTF --watch --interval 60
```

Each poll prints only the delta: challenges that unlocked, prices that moved
under dynamic scoring, and anything solved on the platform. Attachments already
on disk are matched by checksum and not downloaded again, so polling a CTF with
large files stays cheap; `--refresh-attachments` forces a re-download when
organisers republish a file under the same name. The watch stops on Ctrl-C or
once the CTF is no longer running, and backs off if the platform starts failing.

### Challenge notes and environments

Notes are stored as portable Markdown in the challenge directory:

```bash
pwnv challenge note add "Offset is 72 bytes" --section Pwn \
  --challenge RopMaster --ctf ExampleCTF
pwnv challenge note show --challenge RopMaster --ctf ExampleCTF
```

Each challenge can also have an isolated `.venv` managed through `uv`:

```bash
pwnv challenge env add pwntools z3-solver \
  --challenge RopMaster --ctf ExampleCTF
pwnv challenge env run --challenge RopMaster --ctf ExampleCTF python solve.py
```

Flag submission history is stored in workspace configuration. Flags are redacted
unless `pwnv solve --history --show-flags` is explicitly used. Portable workspace
exports remove stored flags and submission history.

For a completely unattended initial setup, combine `--yes` and `--no-install`:

```bash
pwnv init --yes --no-install --ctfs-folder /tmp/ctfs
```

`workspace backup` contains the complete workspace, including remote credentials.
Store its archive securely. Generated virtual environments (`.pwnvenv` and each
challenge's `.venv`) are excluded, since `uv` can rebuild them. `workspace export`
contains metadata only and is the safer format for sharing or moving workspace
structure.

`workspace import` merges by default, so importing a teammate's export adds their
CTFs and challenges without touching your own solves. Records already present are
skipped, which makes re-importing the same file a no-op. Pass `--replace` for the
old behaviour of discarding the current metadata.

Each remote CTF directory gets a `.gitignore` covering `.env` and `.session`, so
committing a shared CTF folder to a team repository does not leak the platform
password or a live session cookie.

-----

## 🤝 Contributing

Contributions to `pwnv` are welcome. Please refer to the [GitHub repository](https://github.com/CarixoHD/pwnv) to report issues, propose features, or submit pull requests.

-----

## 📄 License

`pwnv` is distributed under the MIT License. See the `LICENSE` file for further details.

MIT © [Shayan Alinejad](mailto:shayan.alinejad@proton.me)
