# Remote Platforms

`pwnv` talks to CTF platforms through
[`ctfbridge`](https://github.com/bjornmorten/ctfbridge), which detects the
platform from a URL and exposes one interface across CTFd, rCTF, GZCTF, Berg,
EPT and others.

## Connecting

```bash
pwnv ctf add DemoCTF --url https://demo.ctfd.io/ --username user --password password
```

Token authentication works the same way:

```bash
pwnv ctf add DemoCTF --url https://demo.ctfd.io/ --token 'ctfd_...'
```

### Credentials without shell history

Every credential option has an environment variable, which keeps secrets out of
your history and out of `ps`:

| Variable | Replaces |
| :--- | :--- |
| `PWNV_CTF_USERNAME` | `--username` |
| `PWNV_CTF_PASSWORD` | `--password` |
| `PWNV_CTF_TOKEN` | `--token` |

Credentials are stored in the CTF directory's `.env`, and the session in
`.session`. Both are covered by a generated `.gitignore`.

## Syncing

```bash
pwnv ctf sync --ctf DemoCTF
```

A sync creates directories for new challenges and updates existing ones: points,
category, solved state, description, services, tags and attachments. Your local
tags, flags, solve progress and directory paths are preserved — a sync never
overwrites your own work with the platform's view of it.

Output is a delta rather than the whole scoreboard:

```
[DemoCTF]
  + Baby ROP
  ~ Sanity Check (100 -> 80 pts, solved on platform)
  12 unchanged, 1 attachment set(s) downloaded, 4 already on disk
```

### Watching

```bash
pwnv ctf sync --ctf DemoCTF --watch --interval 60
```

The watch stops on Ctrl-C or once the CTF is no longer running, and backs off if
the platform starts returning errors. Attachments already on disk are matched by
checksum and not fetched again, so polling an event with large handouts stays
cheap. `--refresh-attachments` forces a re-download when organisers republish a
file under the same name.

## When detection fails

`ctfbridge` identifies most platforms from the landing page. An event running a
custom frontend over a standard backend can defeat that, since there is no
recognisable markup to match.

If `pwnv ctf add` reports that it could not identify the platform, confirm what
the API looks like before assuming it is unsupported:

```bash
curl -s https://ctf.example.org/api/v1/users/me
```

An rCTF backend answers with `{"kind":"badToken", ...}`; CTFd answers from
`/api/v1/challenges`. Report the URL upstream — detection is a small patch, and
the platform support itself is usually already there.

## Submitting

```bash
pwnv solve --flag 'FLAG{example}'
```

Submission goes through the same client. The challenge is marked solved only on
the platform's say-so.
