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
| 🔄 **Remote Synchronization**| Enables fetching challenges, descriptions, and attachments from CTFd instances using the [`ctfbridge`](https://pypi.org/project/ctfbridge) library. |
| 🚀 **Remote Flag Submission**| Allows direct submission of flags to remote CTF platforms via the command line. |
| 🔌 **Plugin Architecture** | Supports custom Python plugins for automating challenge setup based on predefined categories (e.g., pwn, web). |
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
    cd ~/CTFs/ExampleCTF_Local/pwn/RopMaster/
    # Begin solving the challenge.
    ```
5.  **Mark the challenge as solved:**
    ```bash
    pwnv solve --flag "FLAG{example_flag}"
    # Enter tags when prompted (e.g., "buffer-overflow, ROP").
    ```

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
        "gdbinit": "gdbinit_rop",  # save as gdbinit_rop
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
| `pwnv init` | Initializes the `pwnv` environment and workspace. |
| `pwnv reset` | Removes all `pwnv` configurations and CTF data (exercise caution). |
| | |
| `pwnv ctf add <name>` | Adds a new CTF event (local or remote). |
| `pwnv ctf remove` | Deletes a CTF event and its challenges. |
| `pwnv ctf info` | Displays metadata for a selected CTF. |
| `pwnv ctf sync` | Adds and updates challenges from a remote CTF. |
| `pwnv ctf start` | Sets a CTF's status to 'running'. |
| `pwnv ctf stop` | Sets a CTF's status to 'stopped'. |
| | |
| `pwnv challenge add <name>`| Adds a new challenge, triggering relevant plugins. |
| `pwnv challenge remove` | Deletes a specific challenge. |
| `pwnv challenge info` | Displays metadata for a selected challenge. |
| `pwnv challenge filter` | Lists solved challenges based on specified tags. |
| `pwnv challenge search <QUERY>` | Searches names, descriptions, categories, and tags. |
| `pwnv challenge note add <TEXT>` | Adds a timestamped Markdown note. |
| `pwnv challenge note show` | Displays the current challenge notes. |
| `pwnv challenge env add <PACKAGE...>` | Installs packages in a challenge-local environment. |
| `pwnv challenge env run <COMMAND...>` | Runs a command in the challenge environment. |
| | |
| `pwnv solve` | Marks a challenge as solved and handles flag submission/tagging. |
| `pwnv solve --history` | Displays submission history with flags redacted. |
| `pwnv status` | Displays solved and point progress for the workspace. |
| `pwnv doctor` | Checks workspace configuration, paths, tools, and consistency. |
| | |
| `pwnv plugin add <name>` | Creates a new plugin and its associated template. |
| `pwnv plugin remove` | Deletes an existing plugin file. |
| `pwnv plugin info` | Displays information about registered plugins. |
| `pwnv plugin select` | Assigns a specific plugin to a challenge category. |
| `pwnv workspace backup [PATH]` | Creates a full archive, including challenge files and credentials. |
| `pwnv workspace export [PATH]` | Exports portable workspace metadata without files or credentials. |
| `pwnv workspace import <PATH>` | Imports metadata and rebases paths into the current workspace. |

### Noninteractive usage

Common workflows can be scripted without interactive selectors:

```bash
pwnv ctf add ExampleCTF --local
pwnv ctf add DemoCTF --url https://demo.ctfd.io/ --username user --password password
pwnv ctf sync --ctf DemoCTF
pwnv challenge add RopMaster --ctf ExampleCTF --category pwn
pwnv challenge search rop --ctf ExampleCTF
pwnv challenge search --category pwn --tag rop --min-points 100 --unsolved
pwnv solve --flag 'FLAG{example}' --challenge RopMaster --tags pwn,rop
pwnv solve --history --challenge RopMaster --ctf ExampleCTF
pwnv status --ctf ExampleCTF
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
Store its archive securely. `workspace export` contains metadata only and is the
safer format for sharing or moving workspace structure.

-----

## 🤝 Contributing

Contributions to `pwnv` are welcome. Please refer to the [GitHub repository](https://github.com/CarixoHD/pwnv) to report issues, propose features, or submit pull requests.

-----

## 📄 License

`pwnv` is distributed under the MIT License. See the `LICENSE` file for further details.

MIT © [Shayan Alinejad](mailto:shayan.alinejad@proton.me)
