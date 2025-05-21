# pwnv

**pwnv** is a CLI tool for organizing Capture-the-Flag (CTF) challenges, solving them locally or remotely, and keeping your CTF workflow structured, synchronized, and efficient.

---

## ✨ Features

| Feature              | Description                                                                                      |
|----------------------|--------------------------------------------------------------------------------------------------|
| 🗂 Workspace           | Organized folder structure for CTFs and challenges                                              |
| 📦 Virtual Envs       | Initializes isolated Python environments using [`uv`](https://github.com/astral-sh/uv)          |
| 🔄 Remote Sync        | Pull challenges directly from CTFd instances using [`ctfbridge`](https://pypi.org/project/ctfbridge) |
| 🚀 Flag Submission    | Submit flags to remote platforms directly via CLI                                                |
| 🔎 Challenge Tagging  | Add searchable tags to solved challenges (e.g., `fsop`, `xss`, `buffer overflow`) for easy retrieval |

---

## 🚀 Quickstart

```bash
# 1. Initialize environment
$ pwnv init --ctfs-folder ~/CTF
$ source ~/CTF/.pwnvenv/bin/activate

# 2. Create a CTF
$ pwnv ctf add picoctf-2025

# 3. Add a challenge
$ pwnv challenge add warmup

# 4. Solve the challenge and submit
$ cd warmup
$ pwnv solve
```

---

## 🌐 Fetch from remote CTF

When adding a CTF, you'll have the option to connect to a remote server. If you choose to do so, `pwnv` will pull all challenges into your local workspace — including attachments — and store `.env` and `.session` files for future authenticated access. All of this is powered by [`ctfbridge`](https://pypi.org/project/ctfbridge).

---

## 🧰 Commands

```
pwnv init                 Initialize a new workspace (creates folders, installs deps)
pwnv reset                Delete config files and/or workspace for a fresh new start
pwnv ctf add              Add a CTF (local or remote)
pwnv ctf remove           Remove a CTF and all associated challenges
pwnv ctf start/stop       Mark a CTF as active or inactive
pwnv challenge add        Add a challenge to a CTF
pwnv challenge remove     Remove a challenge from a CTF
pwnv challenge filter     List solved challenges by tags
pwnv challenge info       View metadata for a challenge
pwnv solve                Mark a challenge as solved (optional: submit flag to server)
```

Use `--help` on any subcommand for more info.

---

## 🏗️ Installation

### Via pip

```bash
pip install pwnv
```

### From source (recommended for dev)

```bash
git clone https://github.com/CarixoHD/pwnv
cd pwnv
pip install -e .
```

---


## 📄 License

MIT © [Shayan Alinejad](mailto:shayan.alinejad@proton.me)
