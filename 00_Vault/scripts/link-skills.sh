#!/bin/bash
# Link local agent tools to the vault's skill list (20_Agents/skills).
#
#   00_Vault/scripts/link-skills.sh          show what would change (no changes)
#   00_Vault/scripts/link-skills.sh apply    make the changes
#
# - Directory links: each root in DIR_LINK_ROOTS becomes a symlink to <vault>/20_Agents/skills,
#   so adding or removing a skill in the vault changes that tool's skill list at once.
#   An existing real directory is moved aside to <root>.bak-<timestamp> (never deleted); its
#   symlinked entries are recreated with their resolved absolute target (dead links are skipped)
#   and its copied skills are copied into the vault skill list
#   (both are git-ignored there), unless the vault already has a skill of that name.
# - Per-skill links: directories managed by another program (PER_SKILL_ROOTS) are not replaced;
#   each of my skills (submodules under 20_Agents/skills) gets its own link there, and links that
#   point at a skill no longer in the vault are removed. Roots that do not exist are skipped.
#
# Override the lists with colon-separated paths:
#   VAULT_DIR_LINK_ROOTS="$HOME/.claude/skills" VAULT_PER_SKILL_ROOTS="$HOME/.agents/skills" ...
# Runs on the bash 3.2 that ships with macOS.
set -eu

MODE="${1:-check}"
case "$MODE" in check|apply) ;; *) echo "usage: $0 [check|apply]" >&2; exit 2 ;; esac

VAULT="$(cd "$(dirname "$0")/../.." && pwd -P)"
SKILLS="$VAULT/20_Agents/skills"
if [ ! -f "$VAULT/AGENTS.md" ] || [ ! -d "$VAULT/20_Agents" ]; then
  echo "vault not found at $VAULT" >&2
  exit 1
fi

if [ -n "${VAULT_DIR_LINK_ROOTS:-}" ]; then
  IFS=: read -r -a DIR_LINK_ROOTS <<< "$VAULT_DIR_LINK_ROOTS"
else
  DIR_LINK_ROOTS=("$HOME/.claude/skills")
fi
if [ -n "${VAULT_PER_SKILL_ROOTS:-}" ]; then
  IFS=: read -r -a PER_SKILL_ROOTS <<< "$VAULT_PER_SKILL_ROOTS"
else
  PER_SKILL_ROOTS=(
    "$HOME/.agents/skills"
    "$HOME/.codex/skills"
    "$HOME/.cursor/skills"
    "$HOME/.gemini/skills"
    "$HOME/.pi/agent/skills"
    "$HOME/.copilot/skills"
    "$HOME/.factory/skills"
  )
  orca_accounts="$HOME/Library/Application Support/orca/codex-accounts"
  if [ -d "$orca_accounts" ]; then
    for home in "$orca_accounts"/*/home; do
      [ -d "$home" ] && PER_SKILL_ROOTS+=("$home/skills")
    done
  fi
fi

say() { printf '%s\n' "$*"; }
act() {  # act <description> <command...>: print, and run only in apply mode
  local what="$1"; shift
  if [ "$MODE" = apply ]; then say "  + $what"; "$@"; else say "  ~ $what"; fi
}
resolved() { (cd "$1" 2>/dev/null && pwd -P) || true; }

# ---- 1. submodules (my skills and tools) ----
say "[submodules]"
uninit="$(git -C "$VAULT" submodule status 2>/dev/null | grep '^-' || true)"
if [ -n "$uninit" ]; then
  act "git submodule update --init --recursive" git -C "$VAULT" submodule update --init --recursive
else
  say "  = all initialized"
fi
mkdir -p "$SKILLS"

MY_SKILLS=()
while IFS= read -r p; do
  case "$p" in 20_Agents/skills/*) MY_SKILLS+=("${p#20_Agents/skills/}") ;; esac
done < <(git -C "$VAULT" config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}')
say "  my skills: ${MY_SKILLS[*]:-(none)}"

# ---- 2. directory links ----
for root in "${DIR_LINK_ROOTS[@]}"; do
  say "[dir link] $root -> $SKILLS"
  if [ -L "$root" ]; then
    if [ "$(resolved "$root")" = "$SKILLS" ]; then say "  = already linked"; continue; fi
    act "relink (was -> $(readlink "$root"))" ln -sfn "$SKILLS" "$root"
    continue
  fi
  if [ -d "$root" ]; then
    bak="$root.bak-$(date +%Y%m%d-%H%M%S)"
    act "move existing directory to $bak" mv "$root" "$bak"
    src="$bak"; [ "$MODE" = apply ] || src="$root"
    for entry in "$src"/* ; do
      [ -e "$entry" ] || [ -L "$entry" ] || continue
      name="$(basename "$entry")"
      if [ -e "$SKILLS/$name" ] || [ -L "$SKILLS/$name" ]; then
        say "  = keep vault's $name (old entry left in backup)"
      elif [ -L "$entry" ]; then
        # recreate with the resolved absolute target — a relative target would break at the new location
        abs="$(resolved "$entry")"
        if [ -z "$abs" ]; then
          say "  ! skip dead link $name -> $(readlink "$entry") (left in backup)"
        else
          act "recreate link $name -> $abs" ln -s "$abs" "$SKILLS/$name"
        fi
      elif [ -d "$entry" ]; then
        act "copy skill $name into the vault list (git-ignored)" cp -R "$entry" "$SKILLS/$name"
      fi
    done
  fi
  act "link $root" mkdir -p "$(dirname "$root")"
  act "ln -s $SKILLS $root" ln -s "$SKILLS" "$root"
done

# ---- 3. per-skill links ----
for root in "${PER_SKILL_ROOTS[@]}"; do
  [ -d "$root" ] || continue
  say "[per-skill] $root"
  for s in ${MY_SKILLS[@]+"${MY_SKILLS[@]}"}; do
    target="$root/$s"
    if [ -L "$target" ]; then
      if [ "$(resolved "$target")" = "$SKILLS/$s" ]; then say "  = $s"; continue; fi
      act "relink $s (was -> $(readlink "$target"))" ln -sfn "$SKILLS/$s" "$target"
    elif [ -e "$target" ]; then
      say "  ! $s exists as a real file/directory there; left alone"
    else
      act "link $s" ln -s "$SKILLS/$s" "$target"
    fi
  done
  for link in "$root"/*; do
    [ -L "$link" ] || continue
    case "$(readlink "$link")" in
      "$SKILLS"/*) [ -e "$link" ] || act "remove stale link $(basename "$link")" rm "$link" ;;
    esac
  done
done

[ "$MODE" = apply ] || say "(check only — run with 'apply' to make these changes)"
