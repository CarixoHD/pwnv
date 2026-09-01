# pwnv

A CTF workspace manager for the command line.

`pwnv` gives a CTF the same structure twice in a row: one folder per event, one
folder per challenge, one virtual environment you did not have to think about,
and a solver script that already knows the host and port. It talks to remote
platforms through [`ctfbridge`](https://github.com/bjornmorten/ctfbridge), so the
challenges, descriptions and attachments arrive without a browser.

```bash
pip install pwnv
pwnv init --ctfs-folder ~/CTFs
```

## What it does

<div class="grid cards" markdown>

- :material-folder-multiple: **Structured workspace**

    One directory layout for every event, so a challenge from last year is
    exactly where you expect it.

- :material-cloud-download: **Remote sync**

    Pull challenges, descriptions and attachments from CTFd, rCTF, GZCTF and
    friends. `--watch` follows a live event and reports only the delta.

- :material-flag-checkered: **Flag submission**

    `pwnv solve` submits to the platform, records the attempt, and only marks a
    challenge solved when the platform agrees.

- :material-puzzle: **Plugins and templates**

    Category-specific setup that runs when a challenge is created. Ships with a
    working pwn plugin and a pwntools ROP template.

- :material-directions: **Fast navigation**

    `pwncd baby-rop` puts you in the challenge directory; no argument opens a
    fuzzy picker.

- :material-code-braces: **Made to be scripted**

    Every read command speaks `--json`, and solve scripts read live challenge
    metadata off a single object.

</div>

## The part worth reading first

A solve script should not have to be told where the challenge lives:

```python
from pwn import *
from pwnv import challenge

io = remote(challenge.service.host, challenge.service.port)

log.info(f"{challenge.name} · {challenge.value} pts · {challenge.category}")
```

`challenge` is the ctfbridge challenge model, rebuilt from the workspace, so
everything the platform published is on it. The values are read when the script
runs rather than baked in when the file was created, so a service that moves
mid-event does not leave you editing scripts. See
[The challenge object](api/challenge.md).

## Where to go next

| If you want to | Read |
| :--- | :--- |
| Get it installed | [Installation](getting-started/installation.md) |
| Run your first event | [Quickstart](getting-started/quickstart.md) |
| Understand the folder layout | [Workspace Layout](getting-started/workspace.md) |
| Connect to a platform | [Remote Platforms](guide/remote.md) |
| Automate your setup | [Plugins and Templates](guide/plugins.md) |
| Drive `pwnv` from another tool | [Scripting and Automation](guide/automation.md) |
| Move everything to a new machine | [Backup and Moving](guide/backup.md) |
| Help out | [Contributing](dev/index.md) |
