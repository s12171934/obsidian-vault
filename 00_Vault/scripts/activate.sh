#!/bin/bash
# Activate the vault on this machine: local domain indexes and skill links.
#
#   00_Vault/scripts/activate.sh          show what would change (no changes)
#   00_Vault/scripts/activate.sh apply    make the changes
#
# 1. local_index.py — builds the git-ignored _index.md of 10_Projects · 30_Automations · 50_Knowledge
#    from their tracked rules/, and an empty CHANGE_LOG.md if missing.
# 2. link-skills.sh — initializes submodules and links tool skill directories to 20_Agents/skills.
# Safe to run again; each step only changes what differs.
set -eu
MODE="${1:-check}"
case "$MODE" in check|apply) ;; *) echo "usage: $0 [check|apply]" >&2; exit 2 ;; esac
HERE="$(cd "$(dirname "$0")" && pwd -P)"

echo "== local domain indexes =="
python3 "$HERE/local_index.py" "$MODE"
echo
echo "== skill links =="
"$HERE/link-skills.sh" "$MODE"
