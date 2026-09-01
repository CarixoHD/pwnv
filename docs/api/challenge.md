# The challenge object

```python
from pwnv import challenge
```

What you get is a
[`ctfbridge.models.challenge.Challenge`](https://github.com/bjornmorten/ctfbridge)
— the same model the sync fetched from the platform, rebuilt from the workspace.
There is no pwnv wrapper on top of it, so whatever ctfbridge exposes is what a
solve script gets.

## Why it exists

A scaffolded solve script has the host and port written into it as literals.
That holds until the platform moves the service, or until you copy the script to
the next challenge and edit constants a lookup could have answered.

```python
# before
p = remote("chal.example.org", 31337)

# after
p = remote(challenge.service.host, challenge.service.port)
```

The values are read when the script runs, not when the file was created.

## What is on it

```python
challenge.name              # 'Baby ROP'
challenge.value             # 250
challenge.category          # 'pwn'      (first of challenge.categories)
challenge.description
challenge.tags              # ['rop', 'nx']
challenge.solved            # True / False
challenge.author            # first of challenge.authors

challenge.service           # first Service, or None
challenge.service.host      # 'chal.example.org'
challenge.service.port      # 31337
challenge.service.url       # for web challenges
challenge.service.raw       # 'nc chal.example.org 31337'
challenge.services          # all of them
challenge.has_services

challenge.attachments       # AttachmentCollection: iterate, index, len()
challenge.attachments[0].name
challenge.attachments[0].local_path
```

The full field list is ctfbridge's, not ours — see its
[challenge model](https://github.com/bjornmorten/ctfbridge) for everything else,
including `normalized_categories`, `difficulty` and `flag_format`.

## What pwnv adds

Two fields, because they are local facts the platform never sends:

| | |
| :--- | :--- |
| `challenge.path` | The challenge directory, for a script started from somewhere else |
| `challenge.flag` | The flag you recorded with `pwnv solve` |

## Resolution

`challenge` is resolved on import, from the working directory, by walking up
until it finds a challenge. Importing it outside one raises `NoChallengeError`
with the directory it looked from.

The workspace is re-read on every resolution, so a sync that ran while your
script or REPL was open is picked up. In a long-lived process, ask again:

```python
from pwnv.api import current

challenge = current()               # the working directory
challenge = current("/path/to/it")  # or a specific one
```

## Reference

::: pwnv.api
