# Backup and Moving

Two formats, for two different jobs.

| | `workspace backup` / `restore` | `workspace export` / `import` |
| :--- | :--- | :--- |
| Contains | Everything: challenge files, notes, solve scripts, `.env`, `.session` | Metadata only: CTFs, challenges, tags, points |
| Flags | Kept | Stripped, along with submission history |
| Format | `.tar.gz` | `.json` |
| For | Moving your own workspace to another machine | Sharing a CTF's structure with a teammate |

The split is about credentials. A backup is a copy of your workspace including
the passwords and session cookies it holds, so it belongs on your own disk. An
export is safe to put in a team repository.

## Moving to a new machine

### On the old machine

```bash
pwnv workspace backup ~/pwnv-move
```

That writes `~/pwnv-move.tar.gz` containing the config and the whole CTF tree.
Virtualenvs are left out on purpose — `.pwnvenv` and every challenge `.venv` are
rebuilt by `uv` faster than a tarball can carry them, and they are full of paths
that would be wrong on the other side anyway.

### On the new machine

```bash
pip install pwnv                       # or: uv tool install pwnv
pwnv init --ctfs-folder ~/CTFs
pwnv workspace restore ~/pwnv-move.tar.gz
```

`pwnv init` builds the environment; `restore` puts the CTFs back under the new
CTF root. The absolute paths the backup recorded on the old machine do not come
with it — every record is rebased onto `~/CTFs`, wherever that is now.

```
✓ Workspace restored from /home/you/pwnv-move.tar.gz
info: Copied 214 file(s) into the CTF folder.
info: Added 6 CTFs and 143 challenges; skipped 0 CTFs and 0 already present.
```

Then check it landed:

```bash
pwnv status
pwncd baby-rop
```

## What restore will not do

**It will not overwrite your files.** Anything already on disk is left alone, so
a restore can be re-run over a workspace that is half there — after a transfer
that died at 80%, for instance. Pass `--force` when the archive is the version
you want to keep:

```bash
pwnv workspace restore ~/pwnv-move.tar.gz --force
```

**It will not discard your metadata.** Records already present are skipped, so
restoring the same archive twice adds nothing the second time. `--replace`
throws away the current metadata first, and asks before it does.

!!! note "Directory names are preserved"

    `workspace import` recreates directories from challenge names, because an
    export has no files to place. A backup does, so `restore` keeps the layout
    the archive was made from — including the suffixes pwnv added when two
    challenges in one CTF wanted the same directory name.

## Sharing without sharing secrets

```bash
pwnv workspace export shared.json
```

No flags, no submission history, no credentials, no challenge files — just the
structure. A teammate imports it into their own workspace:

```bash
pwnv workspace import shared.json
```

An import merges: their solves are untouched, and records already present are
skipped, which makes re-importing the same file a no-op. `--replace` is there
for the rare case where you want the file to win outright.

## Keeping a backup current

`workspace backup` is a full copy every time, not an incremental one, so
scheduling it is a matter of taste. During an event, after each solve session is
usually enough:

```bash
pwnv workspace backup ~/backups/pwnv-$(date +%F) --force
```

Treat those archives the way you treat the `.env` files inside them.
