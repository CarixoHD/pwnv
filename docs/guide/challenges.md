# Challenges

## Adding

```bash
pwnv challenge add RopMaster --ctf ExampleCTF --category pwn
```

Omit either option and `pwnv` asks. Omit `--ctf` inside a CTF directory and it
uses the one you are standing in. Adding a challenge creates its directory, runs
the plugin selected for its category, and renders that plugin's templates.

## Looking at one

```bash
pwnv challenge info                      # the one you are in
pwnv challenge info --challenge RopMaster
pwnv challenge info --ctf DemoCTF --json
```

The rendered view includes the fetched description, the connection string, the
author, and any attachments. `--json` gives you the same record as data; see
[JSON payloads](../api/json.md).

## Searching

```bash
pwnv challenge search rop
pwnv challenge search --category pwn --tag rop --min-points 100 --unsolved
pwnv challenge search --ctf DemoCTF --has-service
```

Search covers names, descriptions, categories and tags. With only `--ctf` and no
query, it lists that event. Every filter combines, and `--json` works here too.

## Solving

```bash
pwnv solve --flag 'FLAG{example}' --tags pwn,rop
```

For a remote CTF the flag is submitted first, and the challenge is only marked
solved if the platform accepts it. A rejected flag is still recorded in the
history, and the command exits non-zero.

```bash
pwnv solve --history                 # flags redacted
pwnv solve --history --show-flags    # explicit opt-in
```

## Tagging and recall

Tags are the reason to bother recording solves at all — six months later they are
how you find the challenge you half-remember.

```bash
pwnv challenge filter                # pick tags, see matching solved challenges
pwnv challenge search --tag heap --tag uaf
```

## Notes

Notes live in the challenge directory as plain Markdown, so they survive `pwnv`
entirely and can be committed with the rest of your work.

```bash
pwnv challenge note add "Offset is 72 bytes" --section Pwn
pwnv challenge note show
```

## Re-scaffolding

`pwnv challenge add` runs the plugin for the challenge's own category. Sometimes
you want a different one — a web challenge with a binary attached still deserves
the pwn template:

```bash
pwnv challenge scaffold --category pwn --suffix _pwn
pwnv challenge scaffold --plugin my_pwn_plugin --force
```

This runs the chosen plugin and renders its templates. It does not change the
challenge's category or anything else about the record. Existing files are left
alone unless you pass `--force`, and `--suffix` writes `solve_pwn.py` next to the
`solve.py` you are already working in.

## Removing

```bash
pwnv challenge remove --challenge RopMaster --ctf ExampleCTF --yes
```

This deletes the directory as well as the record. `--yes` skips the prompt.
