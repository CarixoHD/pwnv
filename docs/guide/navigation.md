# Navigation

A CTF workspace is a deep tree, and `cd ~/ctfs/SomeCTF/pwn/baby-rop` is not a
thing anyone should type twice.

## `pwncd`

```bash
eval "$(pwnv shell-init)"          # bash, zsh
pwnv shell-init --shell fish | source
```

Put that line in your rc file and you get a `pwncd` function:

```bash
pwncd baby-rop          # jump straight there
pwncd                   # fuzzy-pick from every challenge
pwncd --ctf DemoCTF     # fuzzy-pick within one event
```

!!! note "Why a shell function and not a command"

    A child process cannot change its parent's directory. `pwnv challenge path`
    prints the directory and nothing else, and the shell function does the
    `cd`. The picker draws on the terminal rather than on stdout, so it still
    works inside the command substitution.

## `pwnv challenge path`

The same primitive, usable on its own:

```bash
cd "$(pwnv challenge path baby-rop)"
code "$(pwnv challenge path)"
tar czf handout.tgz -C "$(pwnv challenge path baby-rop)" .
```

## Working from where you stand

Most commands infer the challenge from your current directory, so once you are
inside one there is nothing left to specify:

```bash
pwnv challenge info
pwnv solve --flag 'FLAG{...}'
pwnv challenge note add "ret2libc, offset 72"
pwnv challenge env run python solve.py
```

## Status

```bash
pwnv status                     # every CTF, at a glance
pwnv status --ctf DemoCTF -d    # per-category progress, recent solves, what is left
```
