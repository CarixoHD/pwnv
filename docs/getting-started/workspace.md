# Workspace Layout

`pwnv` keeps two things in two places: **records** in a configuration file, and
**files** in a directory tree. Neither is a database you have to respect — the
tree is ordinary directories, and the config is JSON.

## The tree

```
~/CTFs/
├── .pwnvenv/                  # shared environment built by `pwnv init`
├── ExampleCTF/
│   ├── pwn/
│   │   └── RopMaster/
│   │       ├── solve.py
│   │       └── notes.md
│   └── web/
│       └── WebChallenge/
└── DemoCTF/
    ├── .env                   # platform credentials
    ├── .session               # saved session
    ├── .gitignore             # ignores the two files above
    └── crypto/
        └── CryptoChallenge/
```

Every remote CTF directory gets a `.gitignore` covering `.env` and `.session`, so
pushing a shared CTF folder to a team repository does not leak the platform
password or a live session cookie.

## The configuration

The config file records CTFs, challenges, tags and submission history. It is
found by walking up from the current directory looking for `pwnv_config.json`,
and falling back to the platform config directory (`~/.config/pwnv/` on Linux).

Set `PWNV_CONFIG` to point at a specific file. That is how the devcontainer keeps
its state inside the workspace, and how the test suite stays out of your real
config.

```bash
PWNV_CONFIG=/tmp/scratch/pwnv_config.json pwnv status
```

Writes go through a lock and a temporary file that is renamed into place, so two
`pwnv` processes running at once cannot lose each other's changes — which
matters when a `--watch` sync is running while you submit a flag.

## Alongside the config

The configuration directory also holds:

| Folder | Contents |
| :--- | :--- |
| `plugins/` | One `.py` file per plugin, plus `selection.json` recording which plugin is chosen for each category. |
| `templates/` | Template files organised by category, e.g. `templates/pwn/rop.py`. |

Both are seeded on `pwnv init` with the examples that ship in the package. See
[Plugins and Templates](../guide/plugins.md).

## Environments

There are two layers, and you usually only need the first:

- **The shared CTF environment** at `<ctfs-folder>/.pwnvenv`, built by
  `pwnv init` with `pwntools` and the other defaults.
- **A per-challenge environment**, created on demand when a challenge needs a
  package the shared one should not have:

    ```bash
    pwnv challenge env add z3-solver --challenge CryptoChallenge
    pwnv challenge env run --challenge CryptoChallenge python solve.py
    ```

Neither is backed up by `pwnv workspace backup`, because `uv` can rebuild both
on the other side - see [Backup and Moving](../guide/backup.md) for taking the
rest of the workspace with you.
