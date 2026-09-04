#!/usr/bin/env bash
# install.sh: one-line ZenML installer.
#
#   curl -fsSL https://zenml.io/install | bash
#   curl -fsSL https://zenml.io/install | bash -s -- --no-server
#
# What it does, in order:
#   1. Makes sure `uv` is available (installs it from astral.sh if not).
#   2. Installs zenml[local]. Where depends on where you run it:
#        - inside a Python project (pyproject.toml or uv.lock in the current
#          directory): `uv add` into that project's environment, so your
#          pipelines import zenml next to their own dependencies;
#        - anywhere else: `uv tool install` into an isolated environment, with
#          the `zenml` CLI on PATH (~/.local/bin).
#      --project / --global force either. The default is the `server` extra,
#      so `zenml login --local` can run the server and dashboard on this
#      machine; --no-server installs the slimmer `local` extra (client plus
#      a local SQLite store, no dashboard).
#   3. Installs the ZenML coding-agent skills (zenml-io/skills) from the
#      repository tarball into ~/.agents/skills, plus ~/.claude/skills and
#      ~/.codex/skills when those CLIs are installed. No Node needed.
#   4. Stops there and prints the next commands. Logging in to a server is a
#      decision, so the script does not make it for you.
#
# Nothing here needs sudo. Everything lands under $HOME. Re-running upgrades.
#
# Design shared with the Kitaru installer (zenml-io/kitaru) and follows
# astral.sh/uv/install.sh. ZenML ships as a Python package, not a binary, so uv
# is the one dependency this script will install for you.

# Bash-only, but fail politely under sh/dash/zsh-as-sh. This line is POSIX so
# it runs before the shell reaches any bash syntax below.
if [ -z "${BASH_VERSION:-}" ]; then echo "ZenML's installer needs bash. Run: curl -fsSL https://zenml.io/install | bash" >&2; exit 1; fi

set -euo pipefail

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
ZENML_VERSION="${ZENML_VERSION:-}"            # pin, e.g. 0.96.3
ZENML_PRE="${ZENML_PRE:-0}"                   # allow pre-releases
ZENML_SERVER_EXTRA="${ZENML_SERVER_EXTRA:-1}" # 0: zenml[local] (slimmer client) instead of zenml[server]
ZENML_SKIP_SKILLS="${ZENML_SKIP_SKILLS:-0}"
ZENML_QUIET="${ZENML_QUIET:-0}"
ZENML_VERBOSE="${ZENML_VERBOSE:-0}"
ZENML_WITH=()                                 # extra packages
ZENML_PYTHON="${ZENML_PYTHON:-3.12}"          # uv-managed Python if none suitable (global mode)
ZENML_SCOPE="${ZENML_SCOPE:-auto}"            # auto | project | global
ZENML_SKILLS_REPO="${ZENML_SKILLS_REPO:-zenml-io/skills}"
ZENML_NO_MODIFY_PATH="${ZENML_NO_MODIFY_PATH:-0}"    # leave rc files alone
ZENML_MIN_UV="0.5.0"                                 # older uv lacks the tool flags we use
ZENML_FIRST_SKILL="zenml-pipeline-authoring"         # the skill the closing hint points at

usage() {
  cat <<'USAGE'
Usage: install.sh [options]

  --version=X.Y.Z     Install a specific ZenML version (default: latest)
  --pre               Allow pre-release versions
  --no-server         Install the slimmer zenml[local] instead of zenml[server].
                      `zenml login --local` then needs Docker (--docker) or a
                      re-run of this installer without --no-server
  --with=PKG          Also install PKG into the same environment (repeatable)
  --project           Install into the Python project in the current directory
                      (uv add). Default when a pyproject.toml or uv.lock is here.
  --global            Install into an isolated uv tool environment on PATH.
                      Default anywhere else.
  --no-skills         Skip installing the coding-agent skills
  --no-modify-path    Do not edit shell rc files; you add ~/.local/bin yourself
  --quiet             Only print errors
  --verbose           Print every command
  -h, --help          This text

Environment equivalents: ZENML_VERSION, ZENML_PRE=1, ZENML_SERVER_EXTRA=0,
ZENML_SCOPE=project|global, ZENML_SKIP_SKILLS=1, ZENML_NO_MODIFY_PATH=1,
ZENML_QUIET=1, ZENML_VERBOSE=1, ZENML_PYTHON (default 3.12), NO_COLOR.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version=*) ZENML_VERSION="${1#*=}" ;;
    --version) shift; ZENML_VERSION="${1:-}" ;;
    --pre) ZENML_PRE=1 ;;
    --server) ZENML_SERVER_EXTRA=1 ;;
    --no-server) ZENML_SERVER_EXTRA=0 ;;
    --with=?*) ZENML_WITH+=("${1#*=}") ;;
    --with) shift; [ -n "${1:-}" ] && ZENML_WITH+=("$1") ;;
    --project) ZENML_SCOPE=project ;;
    --global) ZENML_SCOPE=global ;;
    --no-skills) ZENML_SKIP_SKILLS=1 ;;
    --no-modify-path) ZENML_NO_MODIFY_PATH=1 ;;
    --quiet) ZENML_QUIET=1 ;;
    --verbose) ZENML_VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
C_ACCENT=""; C_GREEN=""; C_RED=""; C_DIM=""; C_BOLD=""; C_RESET=""
if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then
  C_ACCENT=$'\033[35m'; C_GREEN=$'\033[32m'; C_RED=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
fi

say()  { [ "$ZENML_QUIET" = "1" ] || printf '%s\n' "$*"; }
step() { [ "$ZENML_QUIET" = "1" ] || printf '%s◇%s %s\n' "$C_ACCENT" "$C_RESET" "$*"; }
ok()   { [ "$ZENML_QUIET" = "1" ] || printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
note() { [ "$ZENML_QUIET" = "1" ] || printf '  %s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }
warn() { printf '%s!%s %s\n' "$C_ACCENT" "$C_RESET" "$*" >&2; }
die()  { printf '%s✕%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
run()  { [ "$ZENML_VERBOSE" = "1" ] && printf '  %s$ %s%s\n' "$C_DIM" "$*" "$C_RESET" >&2; "$@"; }
quiet() {
  # Run a command, showing its output only on failure or --verbose.
  # stdin is /dev/null so a child can never swallow the rest of this script
  # when it is being piped in from curl.
  if [ "$ZENML_VERBOSE" = "1" ]; then run "$@" </dev/null; return $?; fi
  local out status=0; out="$(mktemp)"
  "$@" >"$out" 2>&1 </dev/null || status=$?
  [ "$status" -eq 0 ] || cat "$out" >&2
  rm -f "$out"; return "$status"
}
have() { command -v "$1" >/dev/null 2>&1; }

main() {
# PATH as the user had it, before this script adds anything to it.
ORIG_PATH="$PATH"
# Scratch space for downloads; every early exit below can just return.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  die "Do not run this installer with sudo. It installs into your home directory and needs no root access."
fi

# Windows (Git Bash / MSYS) differs in the venv layout and executable suffix.
IS_WINDOWS=0; EXE=""
case "$(uname -s)" in
  Darwin|Linux) ;;
  MINGW*|MSYS*|CYGWIN*)
    IS_WINDOWS=1; EXE=".exe"
    warn "Windows (Git Bash) detected. Installing; WSL is recommended." ;;
  *) die "Unsupported OS: $(uname -s)" ;;
esac

if ! have curl && ! have wget; then die "Need curl or wget."; fi

fetch_to_stdout() {
  if have curl; then curl -fsSL --proto '=https' --tlsv1.2 "$1"
  else wget -q --https-only -O- "$1"; fi
}

say ""
say "${C_ACCENT}◆${C_RESET} ${C_BOLD}Installing ZenML${C_RESET}"
say ""

# ---------------------------------------------------------------------------
# 1. uv
# ---------------------------------------------------------------------------
ensure_path() {
  case ":$PATH:" in *":$1:"*) ;; *) export PATH="$1:$PATH" ;; esac
}
ensure_path "$HOME/.local/bin"
ensure_path "$HOME/.cargo/bin"

version_ge() {
  # version_ge A B is true if A >= B (dotted numerics only)
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$2" ]
}

uv_version_of() { "$1" --version 2>/dev/null | awk '{print $2}'; }

install_uv() {
  local installer="$TMP/uv-install.sh" ver
  step "Installing uv (Python package manager, from astral.sh)"
  # Download to a file first: `quiet` closes stdin, so piping into `sh -s`
  # would hand the installer an empty script.
  fetch_to_stdout https://astral.sh/uv/install.sh >"$installer" \
    || die "Could not download the uv installer from https://astral.sh/uv/install.sh"
  quiet sh "$installer" --quiet \
    || die "uv install failed. Install it from https://docs.astral.sh/uv/ and re-run."
  # Use the binary we just installed by absolute path, and put its directory
  # in front so an older uv earlier on PATH (or bash's hashed path) can't win.
  UV="$HOME/.local/bin/uv"
  export PATH="$HOME/.local/bin:$PATH"; hash -r
  [ -x "$UV" ] || die "uv installed but $UV is missing. Install it from https://docs.astral.sh/uv/ and re-run."
  ver="$(uv_version_of "$UV")"
  version_ge "$ver" "$ZENML_MIN_UV" \
    || die "uv at $UV is $ver, older than $ZENML_MIN_UV. Install a current uv and re-run."
  ok "uv $ver installed"
}

# $UV is the uv binary used for everything below (absolute path).
UV=""
if have uv; then
  UV="$(command -v uv)"
  UV_VER="$(uv_version_of "$UV")"
  if version_ge "$UV_VER" "$ZENML_MIN_UV"; then
    ok "uv $UV_VER found"
  else
    note "uv $UV_VER is older than $ZENML_MIN_UV; installing a current one alongside it."
    install_uv
  fi
else
  install_uv
fi

persist_path() {
  # `uv tool update-shell` handles bash/zsh/fish when it recognizes the login
  # shell. Cover the rest (Alpine sh, containers, CI images) by appending to
  # ~/.profile when no rc file mentions the directory yet.
  local dir="$1" f
  for f in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.config/fish/config.fish"; do
    [ -f "$f" ] && grep -qs "$dir\|\.local/bin" "$f" && return 0
  done
  # shellcheck disable=SC2016  # $PATH is meant to expand in the user's shell, not here
  printf '\n# Added by the ZenML installer\nexport PATH="%s:$PATH"\n' "$dir" >> "$HOME/.profile"
}

zenml_version_of() {
  # `zenml --version` prints "zenml, version X.Y.Z", on stderr: the CLI
  # reroutes stdout there so that piped command output stays clean.
  "$1" --version 2>&1 </dev/null | awk '/version/ {print $NF; exit}'
}

# ---------------------------------------------------------------------------
# 2. zenml: into this project, or an isolated tool env
# ---------------------------------------------------------------------------
# The bare package is a client that needs a server to talk to; `zenml status`
# on a fresh machine fails with an ImportError without the `local` extra
# (SQLite store). The `server` extra is a superset that adds what `zenml login
# --local` needs to run the server and dashboard on this machine without
# Docker. It is the default so the printed next step just works; --no-server
# opts out of FastAPI, uvicorn and friends.
SPEC="zenml[server]"
[ "$ZENML_SERVER_EXTRA" = "0" ] && SPEC="zenml[local]"
[ -n "$ZENML_VERSION" ] && SPEC="${SPEC}==${ZENML_VERSION}"

PROJECT_DIR="$PWD"
if [ "$ZENML_SCOPE" = "auto" ]; then
  if [ -f "$PROJECT_DIR/pyproject.toml" ] || [ -f "$PROJECT_DIR/uv.lock" ]; then
    ZENML_SCOPE=project
  else
    ZENML_SCOPE=global
  fi
fi

# What `zenml` resolved to on the PATH the user started with, if anything.
# Global mode uses it for the shadowing warning and the new-terminal hint.
RESOLVED_ZENML=""
if [ "$ZENML_SCOPE" = "project" ]; then
  # ---- into the project in the current directory ---------------------------
  # Pipelines import zenml, so it has to live where the pipeline code's
  # dependencies live. `uv add` puts zenml into this project's environment
  # (creating .venv if needed) and records it in pyproject.toml.
  [ -f "$PROJECT_DIR/pyproject.toml" ] || die "--project needs a pyproject.toml in $PROJECT_DIR (run \`uv init\` first, or use --global)."
  step "Installing $SPEC into this project ($PROJECT_DIR)"
  UV_ADD=(add --quiet)
  [ "$ZENML_PRE" = "1" ] && UV_ADD+=(--prerelease allow)
  quiet "$UV" "${UV_ADD[@]}" "$SPEC" "${ZENML_WITH[@]:+${ZENML_WITH[@]}}" \
    || die "uv add failed (uv's message is above; ZenML needs Python >= 3.10). To install outside this project instead: --global"
  VENV_DIR="${UV_PROJECT_ENVIRONMENT:-$PROJECT_DIR/.venv}"
  if [ "$IS_WINDOWS" = "1" ]; then TOOL_BIN="$VENV_DIR/Scripts"; else TOOL_BIN="$VENV_DIR/bin"; fi
  ZENML_BIN="$TOOL_BIN/zenml$EXE"
  [ -x "$ZENML_BIN" ] || die "uv reported success but $ZENML_BIN is missing. Re-run with --verbose."
  ok "zenml $(zenml_version_of "$ZENML_BIN") installed into this project's environment"
  note "environment: $VENV_DIR (recorded in pyproject.toml)"
  note "run it as: uv run zenml ...   (or activate the environment)"
else
  # ---- isolated tool environment on PATH -----------------------------------
  UV_ARGS=(tool install --upgrade --quiet --python "$ZENML_PYTHON")
  [ "$ZENML_PRE" = "1" ] && UV_ARGS+=(--prerelease allow)
  for pkg in "${ZENML_WITH[@]:+${ZENML_WITH[@]}}"; do UV_ARGS+=(--with "$pkg"); done

  step "Installing $SPEC (isolated, on PATH)"
  quiet "$UV" "${UV_ARGS[@]}" "$SPEC" || die "uv tool install failed. Re-run with --verbose for details."

  # uv puts tool executables in its tool bin dir; make sure future shells see it.
  TOOL_BIN="$("$UV" tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
  TOOL_ENV="$("$UV" tool dir 2>/dev/null || echo "$HOME/.local/share/uv/tools")/zenml"
  [ "$IS_WINDOWS" = "1" ] && TOOL_BIN="$(cygpath -u "$TOOL_BIN" 2>/dev/null || echo "$TOOL_BIN")"
  ensure_path "$TOOL_BIN"
  if [ "$ZENML_NO_MODIFY_PATH" = "1" ]; then
    note "Not editing shell rc files (--no-modify-path). Make sure $TOOL_BIN is on your PATH."
  else
    quiet "$UV" tool update-shell || true
    persist_path "$TOOL_BIN"
  fi

  ZENML_BIN="$TOOL_BIN/zenml$EXE"
  [ -x "$ZENML_BIN" ] || die "uv reported success but $ZENML_BIN is missing. Re-run with --verbose."
  ok "zenml $(zenml_version_of "$ZENML_BIN") installed"
  note "isolated environment: $TOOL_ENV   (uv tool; no other Python touched)"
  note "command: $ZENML_BIN"
  # Warn if a different zenml was already reachable on the PATH the user
  # started with (a pip or pipx install, say): depending on their rc order it
  # may keep winning in new terminals.
  hash -r
  RESOLVED_ZENML="$(PATH="$ORIG_PATH" command -v zenml 2>/dev/null || true)"
  if [ -n "$RESOLVED_ZENML" ] && [ "$RESOLVED_ZENML" != "$ZENML_BIN" ]; then
    warn "Another zenml at $RESOLVED_ZENML ($(zenml_version_of "$RESOLVED_ZENML" || echo unknown)) shadows the one just installed. Remove it or put $TOOL_BIN first on PATH."
  fi
fi

# ---------------------------------------------------------------------------
# 3. Coding-agent skills
# ---------------------------------------------------------------------------
# Destinations: ~/.agents/skills is the cross-agent location; ~/.claude and
# ~/.codex get their own copy when that CLI is installed or the dir exists.
SKILL_DESTS=("$HOME/.agents/skills")
if have claude || [ -d "$HOME/.claude" ]; then SKILL_DESTS+=("$HOME/.claude/skills"); fi
if have codex || [ -d "$HOME/.codex" ]; then SKILL_DESTS+=("$HOME/.codex/skills"); fi
SKILL_NAMES=()

skill_name_of() {
  # The `name:` line of a SKILL.md front matter, or the empty string.
  sed -n '/^---$/,/^---$/{s/^name:[[:space:]]*//p;}' "$1" | head -1 | tr -d '"'"'"' '
}

install_skills() {
  # Fetch the repository tarball (no git, no Node, no auth, nothing executed
  # from the current directory) and copy every skill into each destination.
  # A skill is any directory holding a SKILL.md, wherever the repo keeps it
  # (zenml-io/skills is a plugin marketplace, so they sit two levels down).
  # Agents key on a flat <name>/SKILL.md, so each one is copied under the
  # name its own front matter declares. Every mutation is checked; a partial
  # copy is a failure.
  local src="$TMP/skills" url skill name dest
  mkdir -p "$src" || return 1
  url="https://github.com/${ZENML_SKILLS_REPO}/archive/refs/heads/main.tar.gz"
  fetch_to_stdout "$url" | tar -xzf - -C "$src" 2>/dev/null || return 1
  for dest in "${SKILL_DESTS[@]}"; do mkdir -p "$dest" || return 1; done
  while IFS= read -r skill; do
    skill="$(dirname "$skill")"
    name="$(skill_name_of "$skill/SKILL.md")"
    [ -n "$name" ] || name="$(basename "$skill")"
    for dest in "${SKILL_DESTS[@]}"; do
      rm -rf "${dest:?}/${name:?}" || return 1
      cp -R "$skill" "$dest/$name" || return 1
    done
    SKILL_NAMES+=("$name")
  done < <(find "$src" -name SKILL.md -not -path '*/node_modules/*' | sort)
  [ "${#SKILL_NAMES[@]}" -gt 0 ] || return 1
  skills_complete
}

# Postcondition: every skill from the tarball is present in every destination.
skills_complete() {
  local dest name
  for dest in "${SKILL_DESTS[@]}"; do
    for name in "${SKILL_NAMES[@]}"; do
      [ -f "$dest/$name/SKILL.md" ] || return 1
    done
  done
  return 0
}

if [ "$ZENML_SKIP_SKILLS" = "1" ]; then
  note "Skipping skills (--no-skills)"
else
  step "Installing ZenML agent skills ($ZENML_SKILLS_REPO)"
  if install_skills; then
    ok "${#SKILL_NAMES[@]} skills installed into ${SKILL_DESTS[*]}"
  else
    warn "Could not install skills. Later: https://github.com/$ZENML_SKILLS_REPO"
  fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
say ""
say "${C_GREEN}◆${C_RESET} ${C_BOLD}ZenML is installed.${C_RESET}"
say ""
if [ "$ZENML_SCOPE" = "project" ]; then
  # zenml is not on PATH in project mode; every command goes through uv run.
  Z="uv run zenml"
  say "  Installed into this project's environment, so run it as ${C_BOLD}uv run zenml ...${C_RESET}"
  say "  (or activate $VENV_DIR)."
  say ""
else
  Z="zenml"
  if [ "$RESOLVED_ZENML" != "$ZENML_BIN" ]; then
    say "  Open a new terminal so 'zenml' is on your PATH."
    say ""
  fi
fi
say "  Next, in your project directory:"
say ""
say "    ${C_BOLD}$Z init${C_RESET}             mark it as a ZenML repository"
say ""
say "  Then pick where your ZenML server lives:"
say ""
if [ "$ZENML_SERVER_EXTRA" = "1" ]; then
  say "    ${C_BOLD}$Z login --local${C_RESET}    local server and dashboard on this machine. Free, open source."
else
  say "    ${C_BOLD}$Z login --local${C_RESET}    local server and dashboard. Needs the server extra:"
  say "                            re-run this installer without --no-server, or use --local --docker."
fi
say "    ${C_BOLD}$Z login${C_RESET}            managed cloud. 14-day free trial."
say ""
for name in "${SKILL_NAMES[@]:+${SKILL_NAMES[@]}}"; do
  if [ "$name" = "$ZENML_FIRST_SKILL" ]; then
    say "  In your ML project, tell your coding agent:"
    say "    ${C_BOLD}Use $ZENML_FIRST_SKILL to write my first pipeline.${C_RESET}"
    say ""
    break
  fi
done
say "  Check setup:   $Z status"
say "  Docs:          https://docs.zenml.io"
say ""
}

main "$@"
