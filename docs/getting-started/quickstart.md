# Quickstart

This walks through one event end to end, from an empty machine to a submitted
flag.

## 1. Initialise the workspace

```bash
pwnv init --ctfs-folder ~/CTFs
```

This creates the CTF folder, builds a shared virtual environment at
`~/CTFs/.pwnvenv` with `pwntools` and friends, and seeds your configuration
directory with the example plugin and template that ship with `pwnv`.

```bash
source ~/CTFs/.pwnvenv/bin/activate
```

!!! tip "Unattended setup"
    `pwnv init --yes --no-install` skips both the prompts and the package
    install, which is what you want in a container or a CI job. `--no-examples`
    skips the bundled plugin and template.

## 2. Add an event

=== "Local"

    ```bash
    pwnv ctf add ExampleCTF --local
    ```

=== "Remote"

    ```bash
    pwnv ctf add DemoCTF --url https://demo.ctfd.io/ \
      --username user --password password
    ```

    The platform is detected from the URL. Credentials can come from
    `PWNV_CTF_USERNAME` / `PWNV_CTF_PASSWORD` or `PWNV_CTF_TOKEN` instead, which
    keeps them out of your shell history.

## 3. Get the challenges

For a remote event, pull them:

```bash
pwnv ctf sync --ctf DemoCTF
```

For a local one, add them by hand:

```bash
pwnv challenge add RopMaster --ctf ExampleCTF --category pwn
```

Either way the challenge directory is created, the category's plugin runs, and
its template is rendered into a solver script.

## 4. Go there and work

```bash
pwncd RopMaster
```

The scaffolded `solve.py` already knows the challenge:

```python
from pwn import *
from pwnv import challenge

io = remote(challenge.service.host, challenge.service.port)
```

## 5. Submit the flag

```bash
pwnv solve --flag 'FLAG{example}' --tags pwn,rop
```

The flag goes to the platform first. If the platform rejects it, the attempt is
recorded in the history, the challenge stays unsolved, and the command exits
non-zero — so a script cannot mistake a wrong flag for a solve.

## 6. See where you stand

```bash
pwnv status --detail
```

| CTF     | Status  | Kind   | Solved | Points   | Categories |
| ------- | ------- | ------ | -----: | -------: | ---------- |
| DemoCTF | running | remote |   4/23 | 950/3200 | pwn, web   |

`--detail` adds per-category progress, recent solves, and what is left. Add
`--json` to get the same numbers as data.

## Watching a live event

During a CTF, poll instead of re-running sync by hand:

```bash
pwnv ctf sync --ctf DemoCTF --watch --interval 60
```

Each poll prints only what changed: challenges that unlocked, prices that moved
under dynamic scoring, and anything a teammate solved on the platform.
