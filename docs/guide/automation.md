# Scripting and Automation

Two things make `pwnv` scriptable: every command that produces a record can
produce it as JSON, and every solve script can read the challenge it lives in as
a Python object.

## In a solve script

```python
from pwnv import challenge

p = remote(challenge.service.host, challenge.service.port)
elf = ELF(challenge.attachments[0].local_path)
```

`challenge` is the ctfbridge challenge model, so it carries whatever the
platform published. Nothing is baked in at scaffold time: the script keeps
working after a sync moves the service, and copies to the next challenge
unchanged. See [the challenge object](../api/challenge.md).

## On the command line

```bash
pwnv challenge info --json
pwnv challenge search --category pwn --unsolved --json
pwnv ctf info --json
pwnv plugin info --json
pwnv status --json
```

stdout carries the data and nothing else; notices, warnings and errors go to
stderr. That means a pipe stays clean even when a command has something to say:

```bash
pwnv challenge search --unsolved --json | jq -r '.challenges[].name'
pwnv challenge info --json | jq -r '.challenges[0].services[0].host'
```

An empty result set is an answer, not an error — `{"challenges": []}` with exit
code 0, including on a workspace where nothing has been added yet. Commands in
`--json` mode never open a picker, because there is nobody on the far end of a
pipe to answer it.

## Examples

Open every unsolved pwn challenge in your editor:

```bash
pwnv challenge search --category pwn --unsolved --json |
  jq -r '.challenges[].path' |
  xargs -r code
```

Check a service is up before starting:

```bash
read -r host port < <(pwnv challenge info --json | jq -r '.challenges[0].services[0] | "\(.host) \(.port)"')
nc -zv "$host" "$port"
```

Count what is left, per category:

```bash
pwnv challenge search --ctf DemoCTF --unsolved --json |
  jq -r '.challenges[].category' | sort | uniq -c
```

## Watching an event

```bash
pwnv ctf sync --ctf DemoCTF --watch --interval 60
```

New challenges appear on disk as organisers release them. The loop stops when
the CTF ends, and attachments already downloaded are matched by checksum rather
than fetched again.

## Per-challenge environments

When one challenge needs a package the shared environment should not have:

```bash
pwnv challenge env add z3-solver
pwnv challenge env run python solve.py
```

The environment lives in the challenge's own `.venv`, and `env run` puts it on
`PATH` for a single command.

## Backup and transfer

```bash
pwnv workspace backup ~/backups/ctfs        # everything, credentials included
pwnv workspace restore ~/backups/ctfs.tar.gz
pwnv workspace export shared.json           # metadata only, safe to share
pwnv workspace import shared.json
```

Moving to another machine is `init` then `restore`; see
[Backup and Moving](backup.md).
