#!/usr/bin/env bash
# Provision the pwnv devcontainer: system tooling, dev environment, agent CLIs
# and the shared CTF virtual environment.
set -euo pipefail

workspace="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$workspace"

log() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }

log "Installing system packages used by pwntools and friends"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    binutils \
    build-essential \
    file \
    gdb \
    less \
    patchelf \
    strace
rm -rf /var/lib/apt/lists/*

log "Syncing the pwnv development environment"
uv sync --locked

log "Installing the Codex CLI"
if command -v npm >/dev/null 2>&1; then
    npm install -g @openai/codex
else
    echo "npm not available - skipping the Codex CLI"
fi

if [ "${PWNV_SKIP_CTF_INIT:-0}" = "1" ]; then
    log "PWNV_SKIP_CTF_INIT=1 - skipping the CTF workspace bootstrap"
    exit 0
fi

config="${PWNV_CONFIG:-$workspace/.pwnv/pwnv_config.json}"
if [ -f "$config" ]; then
    log "CTF workspace already initialised - checking it"
    uv run --frozen pwnv doctor || true
else
    log "Bootstrapping the CTF workspace (this downloads angr and friends)"
    uv run --frozen pwnv init --yes --ctfs-folder "$workspace/.pwnv/CTF"
fi
