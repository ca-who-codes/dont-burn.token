#!/usr/bin/env bash
# Session initializer — run at the start of any AI session
# Usage: ./session/init.sh [project_root]
#
# What it does:
#   1. Generates/refreshes the project snapshot if stale
#   2. Prints a compact session brief for the AI
#   3. Outputs the load order the AI should follow

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DONTBURN_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="${1:-$(pwd)}"
SNAPSHOT_FILE="$DONTBURN_ROOT/snapshot/project.md"

# ── Colors ─────────────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

# ── Check snapshot freshness ────────────────────────────────────────────────────
snapshot_is_stale() {
  if [[ ! -f "$SNAPSHOT_FILE" ]]; then
    return 0  # stale (missing)
  fi
  local snapshot_mtime
  snapshot_mtime=$(stat -f %m "$SNAPSHOT_FILE" 2>/dev/null || stat -c %Y "$SNAPSHOT_FILE" 2>/dev/null)
  local latest_code_mtime
  # Find most recently modified source file
  latest_code_mtime=$(find "$PROJECT_ROOT" \
    -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/__pycache__/*" \
    -not -path "*/dist/*" -not -path "*/build/*" \
    \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" -o -name "*.rs" \) \
    -newer "$SNAPSHOT_FILE" 2>/dev/null | wc -l | tr -d ' ')

  [[ "$latest_code_mtime" -gt 0 ]]
}

# ── Generate snapshot ───────────────────────────────────────────────────────────
if snapshot_is_stale; then
  echo -e "${YELLOW}Snapshot stale or missing — regenerating...${RESET}"
  python3 "$DONTBURN_ROOT/snapshot/generate.py" "$PROJECT_ROOT" "$SNAPSHOT_FILE"
else
  echo -e "${GREEN}Snapshot up to date${RESET}"
fi

# ── Count corrections ───────────────────────────────────────────────────────────
CORRECTIONS_FILE="$DONTBURN_ROOT/session/corrections.md"
correction_count=0
if [[ -f "$CORRECTIONS_FILE" ]]; then
  correction_count=$(grep -c "^\- \[" "$CORRECTIONS_FILE" 2>/dev/null || echo 0)
fi

# ── Print session brief ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔═ dontburn session brief ════════════════════════╗${RESET}"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}║${RESET}  Project:     $(basename "$PROJECT_ROOT")"
echo -e "${BOLD}║${RESET}  Snapshot:    $(wc -l < "$SNAPSHOT_FILE") lines → $SNAPSHOT_FILE"
echo -e "${BOLD}║${RESET}  Skills:      $(ls "$DONTBURN_ROOT/skills/"*.md 2>/dev/null | grep -v index | wc -l | tr -d ' ') available"
echo -e "${BOLD}║${RESET}  Corrections: $correction_count accumulated"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}╠═ AI load order ═════════════════════════════════╣${RESET}"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}║${RESET}  ${DIM}1.${RESET} CLAUDE.md              (behavior rules)"
echo -e "${BOLD}║${RESET}  ${DIM}2.${RESET} snapshot/project.md    (codebase map)"
echo -e "${BOLD}║${RESET}  ${DIM}3.${RESET} skills/index.md        (skill registry)"
echo -e "${BOLD}║${RESET}  ${DIM}4.${RESET} session/corrections.md (past learnings)"
echo -e "${BOLD}║${RESET}"
echo -e "${BOLD}╚═════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "${DIM}Paste this into your AI session to start:${RESET}"
echo ""
echo "Read CLAUDE.md, then snapshot/project.md, then skills/index.md, then session/corrections.md. Then wait for my task."
echo ""
