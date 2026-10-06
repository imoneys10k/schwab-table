#!/bin/sh
# One-click installer for the schwab-table Claude Skill (macOS / Linux).
#
#   curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
#
# Options (when piping, pass them with `sh -s --`):
#   --dir PATH     install into PATH (default: $CLAUDE_SKILLS_DIR or ~/.claude/skills, + /schwab-performance-table)
#   --skip-deps    do not create the Python venv / install Playwright + Chromium
# Re-running updates an existing install.
set -eu

REPO_URL="${SCHWAB_TABLE_REPO:-https://github.com/imoneys10k/schwab-table}"
SKILL_NAME="schwab-performance-table"
SKILLS_ROOT="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
TARGET=""
SKIP_DEPS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) [ $# -ge 2 ] || { echo "error: --dir needs a path" >&2; exit 2; }; TARGET="$2"; shift 2 ;;
    --skip-deps) SKIP_DEPS=1; shift ;;
    -h|--help) sed -n '2,10p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "error: unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$TARGET" ] || TARGET="$SKILLS_ROOT/$SKILL_NAME"

say() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# 1. Fetch the files -----------------------------------------------------------
mkdir -p "$(dirname "$TARGET")"
if [ -d "$TARGET/.git" ]; then
  command -v git >/dev/null 2>&1 || die "git is required to update $TARGET"
  say "Updating existing install in $TARGET"
  git -C "$TARGET" pull --ff-only
elif command -v git >/dev/null 2>&1 && { [ ! -e "$TARGET" ] || [ -z "$(ls -A "$TARGET" 2>/dev/null)" ]; }; then
  say "Cloning into $TARGET"
  git clone --depth 1 "$REPO_URL.git" "$TARGET"
else
  say "Downloading into $TARGET"
  mkdir -p "$TARGET"
  TARBALL="$REPO_URL/archive/refs/heads/main.tar.gz"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$TARBALL" | tar -xz -C "$TARGET" --strip-components=1
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "$TARBALL" | tar -xz -C "$TARGET" --strip-components=1
  else
    die "need git, curl or wget to download the skill"
  fi
fi

# 2. Python dependencies (only needed to render tables) -------------------------
if [ "$SKIP_DEPS" -eq 1 ]; then
  say "Skipping Python dependencies (--skip-deps)"
else
  PY=""
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  done
  [ -n "$PY" ] || die "Python 3.9+ not found. Install it (https://www.python.org/downloads/), or re-run with --skip-deps."

  say "Creating virtual environment ($TARGET/.venv)"
  "$PY" -m venv "$TARGET/.venv" || die "could not create a venv. On Debian/Ubuntu run: sudo apt install python3-venv"
  VPY="$TARGET/.venv/bin/python"
  say "Installing Playwright"
  "$VPY" -m pip install --quiet --disable-pip-version-check -r "$TARGET/requirements.txt"
  say "Installing Chromium for Playwright (about 100 MB)"
  "$VPY" -m playwright install chromium

  # 3. Smoke test ----------------------------------------------------------------
  say "Smoke test: rendering an example table and an example chart"
  SMOKE="$(mktemp -d)"
  if "$VPY" "$TARGET/render_table.py" "$TARGET/examples/neural9_spec.json" "$SMOKE/table" >/dev/null 2>"$SMOKE/err" \
     && "$VPY" "$TARGET/render_chart.py" "$TARGET/examples/chart_lines_spec.json" "$SMOKE/chart" >/dev/null 2>>"$SMOKE/err"; then
    say "Render OK"
  else
    cat "$SMOKE/err" >&2
    if [ "$(uname -s)" = "Linux" ]; then
      echo "hint: Chromium may be missing system libraries. Try: sudo $VPY -m playwright install-deps chromium" >&2
    fi
    rm -rf "$SMOKE"
    die "smoke test failed"
  fi
  rm -rf "$SMOKE"
fi

if [ "$SKIP_DEPS" -eq 0 ] && [ "$(uname -s)" = "Linux" ] && command -v fc-list >/dev/null 2>&1 && [ -z "$(fc-list :lang=zh 2>/dev/null)" ]; then
  echo "hint: no Chinese font found, so the Chinese version would render as boxes. Install one, e.g. on Debian/Ubuntu: sudo apt install fonts-noto-cjk" >&2
fi

say "Installed to $TARGET"
echo "Restart Claude (or start a new session) so it picks up the skill."
