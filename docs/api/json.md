# JSON payloads

Every command that reports a record accepts `--json`. The shapes below are
produced by [`pwnv.utils.serialize`](#reference) and are the same regardless of
which command emitted them.

## The contract

- **stdout is data.** In `--json` mode, stdout contains one JSON document and
  nothing else.
- **stderr is for humans.** Notices, warnings and errors go there in every mode,
  so a pipe stays parseable even when a command has something to say.
- **No prompts.** A command in `--json` mode resolves its scope from the
  arguments and the working directory. It never opens a picker, because a pipe
  cannot answer one.
- **Empty is not an error.** A query that matches nothing returns an empty list
  and exit code 0.

## `challenges`

Emitted by `pwnv challenge info --json` and `pwnv challenge search --json`.

```json
{
  "challenges": [
    {
      "id": "5f2b...",
      "name": "Baby ROP",
      "ctf": "DemoCTF",
      "category": "pwn",
      "points": 250,
      "solved": false,
      "flag": null,
      "path": "/home/you/ctfs/DemoCTF/pwn/baby-rop",
      "tags": ["rop"],
      "description": "Can you pop a shell?",
      "author": "organiser",
      "slug": "baby-rop",
      "services": [{"type": "tcp", "host": "chal.example.org", "port": 31337}],
      "attachments": [{"name": "vuln", "url": "https://..."}]
    }
  ]
}
```

`category` is the enum's name, `solved` is a plain boolean, and `id` and `path`
are strings.

## `ctfs`

Emitted by `pwnv ctf info --json`.

```json
{
  "ctfs": [
    {
      "id": "1a4c...",
      "name": "DemoCTF",
      "path": "/home/you/ctfs/DemoCTF",
      "url": "https://demo.ctfd.io/",
      "running": true,
      "created_at": "2026-03-14T09:00:00",
      "challenges": 42,
      "solved": 17
    }
  ]
}
```

## `plugins`

Emitted by `pwnv plugin info --json`.

```json
{
  "plugins": [
    {
      "name": "pwn_example",
      "category": "pwn",
      "file": "/home/you/.config/pwnv/plugins/pwn_example.py",
      "selected": true,
      "templates": ["rop.py"]
    }
  ]
}
```

## `status`

`pwnv status --json` reports progress rather than records:

```json
{
  "ctfs": [
    {
      "ctf": "DemoCTF",
      "status": "running",
      "remote": true,
      "solved": 17,
      "challenges": 42,
      "earned_points": 3100,
      "total_points": 9000,
      "categories": ["crypto", "pwn", "web"]
    }
  ],
  "current": {"ctf": "DemoCTF", "challenge": "Baby ROP"}
}
```

With `--detail` a `detail` key is added, holding `categories`, `recent_solves`
and `next_up` for the CTF in focus.

## Reference

::: pwnv.utils.serialize
