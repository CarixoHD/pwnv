# Security Policy

## Supported versions

pwnv is developed on `main` and released from tags. Fixes go into the next
release; older versions are not patched. If you are running an older version,
upgrade before reporting:

```bash
pip install --upgrade pwnv
```

## Reporting a vulnerability

Please do not open a public issue.

Use GitHub's [private vulnerability
reporting](https://github.com/CarixoHD/pwnv/security/advisories/new), or email
<shayan.alinejad@proton.me>. Include the version, what an attacker can do, and
the steps to reproduce it.

You can expect an acknowledgement within a few days, and a fix or an explanation
of why it is not one before any advisory is published.

## What is in scope

pwnv manages a workspace on your own machine and talks to CTF platforms on your
behalf, so the interesting parts are:

- **Stored credentials.** Platform passwords, tokens and session cookies are
  written to the workspace. Anything that exposes them more widely than the
  files they live in is a bug.
- **`pwnv workspace restore` and `import`.** Both read files that may have come
  from someone else. Path traversal out of the CTF folder, or overwriting files
  outside it, is a vulnerability.
- **Attachment downloads.** `pwnv ctf sync` writes files named by a remote
  server into a challenge directory.
- **Anything that executes code you did not ask it to run.**

## What is not

- **Challenge files are hostile by design.** pwnv downloads binaries and scripts
  from CTF platforms and puts them in a directory; it does not run them. Running
  a challenge binary is your decision, and sandboxing it is your job.
- **Plugins and templates are code.** They are Python files in your own
  workspace that pwnv imports and renders on purpose. Installing one you have
  not read is the same as running any other script.
- **The CTF environment.** `pwnv init` installs pwntools, angr and friends from
  PyPI. Vulnerabilities in those belong upstream.
