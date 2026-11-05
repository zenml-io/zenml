#!/usr/bin/env bash
# install.sh — one-line ZenML installer.
#
#   curl -fsSL https://zenml.io/install | bash
#   curl -fsSL https://zenml.io/install | bash -s -- --pre
#
# What it does, in order:
#   1. Makes sure `uv` is available (installs it from astral.sh if not).
#   2. Installs zenml[server]. Where depends on where you run it:
#        - inside a Python project (pyproject.toml or uv.lock in the current
#          directory): `uv add` into that project's environment, because your
#          pipelines import ZenML and have to run next to their own
#          dependencies;
#        - anywhere else: `uv tool install` into an isolated environment, with
#          `zenml` on PATH (~/.local/bin). Good for logging in, managing
#          stacks and browsing runs; running pipelines needs the project form.
#      --project / --global force either.
#   3. Installs the ZenML agent skills (zenml-io/skills) into ~/.agents/skills,
#      plus ~/.claude/skills and ~/.codex/skills when those CLIs are installed.
#   4. Stops there and prints the two ways to get a server: local
#      (`zenml login --local`) or ZenML Pro (`zenml login`). Login is a
#      decision, so the script does not make it for you.
#
# Nothing here needs sudo. Everything lands under $HOME. Re-running upgrades.
#
# Kept parallel to Kitaru's installer (zenml-io/kitaru, install.sh) so both
# can later sit behind one front door. Kitaru's also registers an MCP server;
# this one does not yet, because the ZenML MCP server (zenml-io/mcp-zenml) is
# not pip-installable and needs an API key that only exists after login.

# Bash-only, but fail politely under sh/dash/zsh-as-sh. This line is POSIX so
# it runs before the shell reaches any bash syntax below.
if [ -z "${BASH_VERSION:-}" ]; then echo "ZenML's installer needs bash. Run: curl -fsSL https://zenml.io/install | bash" >&2; exit 1; fi
# macOS /bin/sh is bash in POSIX mode: BASH_VERSION is set, but POSIX mode
# rejects the process substitutions below with a bare syntax error.
case ":${SHELLOPTS:-}:" in *:posix:*) echo "ZenML's installer needs bash, not sh. Run: curl -fsSL https://zenml.io/install | bash" >&2; exit 1 ;; esac

set -euo pipefail

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
# ZENML_INSTALL_* rather than ZENML_*: the ZenML runtime reads ZENML_*
# variables itself (ZENML_VERSION among them), and these are not for it.
ZENML_INSTALL_VERSION="${ZENML_INSTALL_VERSION:-}"          # pin, e.g. 0.98.1
ZENML_INSTALL_PRE="${ZENML_INSTALL_PRE:-0}"                 # allow pre-releases
ZENML_INSTALL_EXTRAS="${ZENML_INSTALL_EXTRAS-server}"       # empty = base package
ZENML_INSTALL_SKIP_SKILLS="${ZENML_INSTALL_SKIP_SKILLS:-0}"
ZENML_INSTALL_QUIET="${ZENML_INSTALL_QUIET:-0}"
ZENML_INSTALL_VERBOSE="${ZENML_INSTALL_VERBOSE:-0}"
ZENML_INSTALL_WITH=()                                       # extra packages, e.g. scikit-learn
ZENML_INSTALL_PYTHON="${ZENML_INSTALL_PYTHON:-}"            # empty: 3.12 globally, see below in a project
# The Pythons ZenML supports, as in pyproject.toml's requires-python (the
# installer smoke workflow checks the two match).
ZENML_SUPPORTED_PYTHON=">=3.10,<3.15"
ZENML_INSTALL_SCOPE="${ZENML_INSTALL_SCOPE:-auto}"          # auto | project | global
ZENML_INSTALL_SKILLS_REPO="${ZENML_INSTALL_SKILLS_REPO:-zenml-io/skills}"
ZENML_INSTALL_NO_MODIFY_PATH="${ZENML_INSTALL_NO_MODIFY_PATH:-0}"  # leave rc files alone
ZENML_INSTALL_MIN_UV="0.5.0"                                # older uv lacks the tool flags we use

usage() {
  cat <<'USAGE'
Usage: install.sh [options]

  --version=X.Y.Z     Install a specific ZenML version (default: latest)
  --pre               Allow pre-release versions
  --extras=LIST       ZenML extras, comma-separated (default: server, which
                      runs the local dashboard). --extras= installs the base
                      package, enough to connect to a deployed server.
  --with=PKG          Also install PKG into the same environment (repeatable),
                      e.g. --with=scikit-learn
  --project           Install into the Python project in the current directory
                      (uv add). Default when a pyproject.toml or uv.lock is here.
  --global            Install into an isolated uv tool environment on PATH.
                      Default anywhere else.
  --python=X.Y        Python for the new environment (default: 3.12 for the
                      isolated one; in a project without a pinned Python, the
                      newest one ZenML supports)
  --no-skills         Skip installing the coding-agent skills
  --no-modify-path    Do not edit shell rc files; you add ~/.local/bin yourself
  --quiet             Only print errors
  --verbose           Print every command
  -h, --help          This text

Environment equivalents: ZENML_INSTALL_VERSION, ZENML_INSTALL_PRE=1,
ZENML_INSTALL_EXTRAS, ZENML_INSTALL_SCOPE=project|global,
ZENML_INSTALL_PYTHON, ZENML_INSTALL_SKIP_SKILLS=1,
ZENML_INSTALL_NO_MODIFY_PATH=1, ZENML_INSTALL_QUIET=1,
ZENML_INSTALL_VERBOSE=1, NO_COLOR.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version=*) ZENML_INSTALL_VERSION="${1#*=}" ;;
    --version) shift; ZENML_INSTALL_VERSION="${1:-}" ;;
    --pre) ZENML_INSTALL_PRE=1 ;;
    --extras=*) ZENML_INSTALL_EXTRAS="${1#*=}" ;;
    --extras) shift; ZENML_INSTALL_EXTRAS="${1:-}" ;;
    --with=*) ZENML_INSTALL_WITH+=("${1#*=}") ;;
    --with) shift; ZENML_INSTALL_WITH+=("${1:-}") ;;
    --python=*) ZENML_INSTALL_PYTHON="${1#*=}" ;;
    --python) shift; ZENML_INSTALL_PYTHON="${1:-}" ;;
    --project) ZENML_INSTALL_SCOPE=project ;;
    --global) ZENML_INSTALL_SCOPE=global ;;
    --no-skills) ZENML_INSTALL_SKIP_SKILLS=1 ;;
    --no-modify-path) ZENML_INSTALL_NO_MODIFY_PATH=1 ;;
    --quiet) ZENML_INSTALL_QUIET=1 ;;
    --verbose) ZENML_INSTALL_VERBOSE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
C_PURPLE=""; C_GREEN=""; C_RED=""; C_DIM=""; C_BOLD=""; C_RESET=""
if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then
  C_PURPLE=$'\033[38;5;99m'; C_GREEN=$'\033[32m'; C_RED=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
fi

say()  { [ "$ZENML_INSTALL_QUIET" = "1" ] || printf '%s\n' "$*"; }
step() { [ "$ZENML_INSTALL_QUIET" = "1" ] || printf '%s◇%s %s\n' "$C_PURPLE" "$C_RESET" "$*"; }
ok()   { [ "$ZENML_INSTALL_QUIET" = "1" ] || printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
note() { [ "$ZENML_INSTALL_QUIET" = "1" ] || printf '  %s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }
warn() { printf '%s!%s %s\n' "$C_PURPLE" "$C_RESET" "$*" >&2; }
die()  { printf '%s✕%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
run()  { [ "$ZENML_INSTALL_VERBOSE" = "1" ] && printf '  %s$ %s%s\n' "$C_DIM" "$*" "$C_RESET" >&2; "$@"; }
quiet() {
  # Run a command, showing its output only on failure or --verbose.
  # stdin is /dev/null so a child can never swallow the rest of this script
  # when it is being piped in from curl.
  if [ "$ZENML_INSTALL_VERBOSE" = "1" ]; then run "$@" </dev/null; return $?; fi
  local out status=0; out="$(mktemp)"
  "$@" >"$out" 2>&1 </dev/null || status=$?
  [ "$status" -eq 0 ] || cat "$out" >&2
  rm -f "$out"; return "$status"
}
have() { command -v "$1" >/dev/null 2>&1; }

main() {
# PATH as the user had it, before this script adds anything to it.
ORIG_PATH="$PATH"
# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
  die "Do not run this installer with sudo. It installs into your home directory and needs no root access."
fi

OS="$(uname -s)"
IS_WINDOWS=0
case "$OS" in
  Darwin|Linux) ;;
  MINGW*|MSYS*|CYGWIN*)
    # Git Bash / MSYS. uv and the CLI install fine; the local server only
    # runs in the foreground (--blocking) there. WSL is the smoother path.
    IS_WINDOWS=1
    warn "Windows (Git Bash) detected. Installing; WSL is recommended for the local server." ;;
  *) die "Unsupported OS: $OS" ;;
esac

if ! have curl && ! have wget; then die "Need curl or wget."; fi

fetch_to_stdout() {
  if have curl; then curl -fsSL --proto '=https' --tlsv1.2 "$1"
  else wget -q --https-only -O- "$1"; fi
}

say ""
say "${C_PURPLE}◆${C_RESET} ${C_BOLD}Installing ZenML${C_RESET}"
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
  # version_ge A B → true if A >= B (dotted numerics only)
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$2" ]
}

uv_version_of() { "$1" --version 2>/dev/null | awk '{print $2}'; }

install_uv() {
  step "Installing uv (Python package manager, from astral.sh)"
  # Download to a file first: `quiet` closes stdin, so piping into `sh -s`
  # would hand the installer an empty script.
  UV_INSTALLER="$(mktemp)"
  trap 'rm -f "$UV_INSTALLER"' EXIT
  fetch_to_stdout https://astral.sh/uv/install.sh >"$UV_INSTALLER" \
    || die "Could not download the uv installer from https://astral.sh/uv/install.sh"
  quiet sh "$UV_INSTALLER" --quiet \
    || die "uv install failed. Install it from https://docs.astral.sh/uv/ and re-run."
  rm -f "$UV_INSTALLER"; trap - EXIT
  # Use the binary we just installed by absolute path, and put its directory
  # in front so an older uv earlier on PATH (or bash's hashed path) can't win.
  UV="$HOME/.local/bin/uv"
  export PATH="$HOME/.local/bin:$PATH"; hash -r
  [ -x "$UV" ] || die "uv installed but $UV is missing. Install it from https://docs.astral.sh/uv/ and re-run."
  version_ge "$(uv_version_of "$UV")" "$ZENML_INSTALL_MIN_UV" \
    || die "uv at $UV is $(uv_version_of "$UV"), older than $ZENML_INSTALL_MIN_UV. Install a current uv and re-run."
  ok "uv $(uv_version_of "$UV") installed"
}

# $UV is the uv binary used for everything below (absolute path).
UV=""
if have uv; then
  UV="$(command -v uv)"
  UV_VER="$(uv_version_of "$UV")"
  if version_ge "$UV_VER" "$ZENML_INSTALL_MIN_UV"; then
    ok "uv $UV_VER found"
  else
    note "uv $UV_VER is older than $ZENML_INSTALL_MIN_UV; installing a current one alongside it."
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
  for f in "$HOME/.bashrc" "$HOME/.zshenv" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.config/fish/config.fish"; do
    [ -f "$f" ] && grep -qs "$dir\|\.local/bin" "$f" && return 0
  done
  # shellcheck disable=SC2016  # $PATH must stay literal: it expands at shell startup.
  printf '\n# Added by the ZenML installer\nexport PATH="%s:$PATH"\n' "$dir" >> "$HOME/.profile"
}

# `zenml --version` prints "zenml, version X.Y.Z" to stderr (the CLI keeps
# stdout for machine-readable output); keep the version only. A broken
# install prints a traceback instead, so fail rather than echo it.
zenml_version_of() {
  local out
  out="$("$1" --version 2>&1)" || return 1
  printf '%s\n' "$out" | tail -1 | awk '{print $NF}'
}

# ---------------------------------------------------------------------------
# 2. zenml: into this project, or an isolated tool env
# ---------------------------------------------------------------------------
SPEC="zenml"
[ -n "$ZENML_INSTALL_EXTRAS" ] && SPEC="zenml[${ZENML_INSTALL_EXTRAS}]"
[ -n "$ZENML_INSTALL_VERSION" ] && SPEC="${SPEC}==${ZENML_INSTALL_VERSION}"
EXTRA_PKGS=()
for pkg in "${ZENML_INSTALL_WITH[@]:-}"; do [ -n "$pkg" ] && EXTRA_PKGS+=("$pkg"); done

PROJECT_DIR="$PWD"
if [ "$ZENML_INSTALL_SCOPE" = "auto" ]; then
  if [ -f "$PROJECT_DIR/pyproject.toml" ] || [ -f "$PROJECT_DIR/uv.lock" ]; then
    ZENML_INSTALL_SCOPE=project
  else
    ZENML_INSTALL_SCOPE=global
  fi
fi

if [ "$ZENML_INSTALL_SCOPE" = "project" ]; then
  # ---- into the project in the current directory ---------------------------
  # Pipelines import ZenML, so it has to live where the pipelines'
  # dependencies live. `uv add` puts zenml into this project's environment
  # (creating .venv if needed) and records it in pyproject.toml.
  [ -f "$PROJECT_DIR/pyproject.toml" ] || die "--project needs a pyproject.toml in $PROJECT_DIR (run \`uv init\` first, or use --global)."
  step "Installing $SPEC into this project ($PROJECT_DIR)"
  VENV_DIR="${UV_PROJECT_ENVIRONMENT:-$PROJECT_DIR/.venv}"
  # A plain `uv add` keeps an already-locked zenml at its old version;
  # --upgrade-package is what makes re-running the installer an upgrade.
  UV_ADD=(add --quiet --upgrade-package zenml)
  [ "$ZENML_INSTALL_PRE" = "1" ] && UV_ADD+=(--prerelease allow)
  # uv ignores upper bounds in a dependency's requires-python, so in a project
  # that has not picked an interpreter it creates .venv on the newest Python
  # it can find or download, which can be one ZenML's dependencies have no
  # wheels for yet (a source build that fails without a Rust toolchain).
  if [ -n "$ZENML_INSTALL_PYTHON" ]; then
    UV_ADD+=(--python "$ZENML_INSTALL_PYTHON")
  elif [ ! -f "$PROJECT_DIR/.python-version" ] && [ ! -d "$VENV_DIR" ]; then
    UV_ADD+=(--python "$ZENML_SUPPORTED_PYTHON")
  fi
  quiet "$UV" "${UV_ADD[@]}" "$SPEC" "${EXTRA_PKGS[@]:+${EXTRA_PKGS[@]}}" \
    || die "uv add failed (uv's message is above; ZenML supports Python $ZENML_SUPPORTED_PYTHON). To install outside this project instead: --global"
  if [ "$IS_WINDOWS" = "1" ]; then TOOL_BIN="$VENV_DIR/Scripts"; else TOOL_BIN="$VENV_DIR/bin"; fi
  ZENML_BIN="$TOOL_BIN/zenml"
  [ -x "$ZENML_BIN" ] || [ -x "$ZENML_BIN.exe" ] || die "uv reported success but $ZENML_BIN is missing. Re-run with --verbose."
  ok "zenml $(zenml_version_of "$ZENML_BIN") installed into this project's environment"
  note "environment: $VENV_DIR (recorded in pyproject.toml)"
  note "run it as: uv run zenml ...   (or activate the environment)"
else
  # ---- isolated tool environment on PATH -----------------------------------
  UV_ARGS=(tool install --upgrade --quiet --python "${ZENML_INSTALL_PYTHON:-3.12}")
  [ "$ZENML_INSTALL_PRE" = "1" ] && UV_ARGS+=(--prerelease allow)
  for pkg in "${EXTRA_PKGS[@]:+${EXTRA_PKGS[@]}}"; do UV_ARGS+=(--with "$pkg"); done

  step "Installing $SPEC (isolated, on PATH)"
  quiet "$UV" "${UV_ARGS[@]}" "$SPEC" || die "uv tool install failed. Re-run with --verbose for details."

  # uv puts tool executables in its tool bin dir; make sure future shells see it.
  TOOL_BIN="$("$UV" tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
  TOOL_ENV="$("$UV" tool dir 2>/dev/null || echo "$HOME/.local/share/uv/tools")/zenml"
  [ "$IS_WINDOWS" = "1" ] && TOOL_BIN="$(cygpath -u "$TOOL_BIN" 2>/dev/null || echo "$TOOL_BIN")"
  if [ "$ZENML_INSTALL_NO_MODIFY_PATH" = "1" ]; then
    note "Not editing shell rc files (--no-modify-path). Make sure $TOOL_BIN is on your PATH."
  else
    # With the user's own PATH: `update-shell` is a no-op when the directory
    # is already on PATH, and this script has put it there by now. Best
    # effort and silent: it exits with an error when an rc file already
    # sources uv's env script (uv's own installer adds one), which is fine,
    # and persist_path covers shells it does not know.
    UPDATE_SHELL_OUT=/dev/null
    [ "$ZENML_INSTALL_VERBOSE" = "1" ] && UPDATE_SHELL_OUT=/dev/stderr
    run env PATH="$ORIG_PATH" "$UV" tool update-shell </dev/null >"$UPDATE_SHELL_OUT" 2>&1 || true
    persist_path "$TOOL_BIN"
  fi
  ensure_path "$TOOL_BIN"

  ZENML_BIN="$TOOL_BIN/zenml"
  [ -x "$ZENML_BIN" ] || [ -x "$ZENML_BIN.exe" ] || die "uv reported success but $ZENML_BIN is missing. Re-run with --verbose."
  ok "zenml $(zenml_version_of "$ZENML_BIN") installed"
  note "isolated environment: $TOOL_ENV   (uv tool; no other Python touched)"
  note "command: $TOOL_BIN/zenml"
  # Warn if a different zenml was already reachable on the PATH the user
  # started with (a pip install in an active virtualenv, say): depending on
  # their rc order it may keep winning in new terminals.
  hash -r
  RESOLVED_ZENML="$(PATH="$ORIG_PATH" command -v zenml 2>/dev/null || true)"
  case "$RESOLVED_ZENML" in
    "$ZENML_BIN"|"$ZENML_BIN.exe") ZENML_ON_ORIG_PATH=1 ;;
    *) ZENML_ON_ORIG_PATH=0 ;;
  esac
  if [ -n "$RESOLVED_ZENML" ] && [ "$ZENML_ON_ORIG_PATH" = "0" ]; then
    warn "Another zenml at $RESOLVED_ZENML shadows the one just installed. Remove it or put $TOOL_BIN first on PATH."
  fi
fi

# ---------------------------------------------------------------------------
# 3. Coding-agent skills
# ---------------------------------------------------------------------------
# Destinations: ~/.agents/skills is the cross-agent location; ~/.claude and
# ~/.codex get their own copy when that CLI is installed or the dir exists.
skill_destinations() {
  echo "$HOME/.agents/skills"
  if have claude || [ -d "$HOME/.claude" ]; then echo "$HOME/.claude/skills"; fi
  if have codex || [ -d "$HOME/.codex" ]; then echo "$HOME/.codex/skills"; fi
}

skill_name() {
  # The `name:` field of a SKILL.md frontmatter block.
  awk 'NR == 1 { if ($0 !~ /^---/) exit; next }
       /^---/ { exit }
       /^name:/ { sub(/\r$/, ""); sub(/^name:[[:space:]]*/, ""); gsub(/["\047]/, ""); print; exit }' "$1"
}

install_skills() {
  # Fetch the repository tarball (no git, no Node, no auth, nothing executed
  # from the current directory) and copy every skill into each destination.
  # Every mutation is checked; a partial copy is a failure.
  local tmp url src skill_md name dest
  tmp="$(mktemp -d)" || return 1
  url="https://github.com/${ZENML_INSTALL_SKILLS_REPO}/archive/refs/heads/main.tar.gz"
  if ! fetch_to_stdout "$url" | tar -xzf - -C "$tmp" 2>/dev/null; then
    rm -rf "$tmp"; return 1
  fi
  # zenml-io/skills is a Claude Code plugin marketplace
  # (skills/<plugin>/skills/<dir>/SKILL.md) whose <dir> names are generic
  # (scoping, quick-wins). Each skill is staged under its frontmatter name
  # instead (zenml-scoping, airflow-to-zenml-migration), and only when that
  # is a plain skill name mentioning zenml: it is about to be `rm -rf`'d in
  # each destination, so it must never match a user's own skill or a path.
  local valid_name='^[a-z0-9-]*zenml[a-z0-9-]*$'
  src="$tmp/by-name"
  mkdir "$src" || { rm -rf "$tmp"; return 1; }
  SKILL_NAMES=()
  while IFS= read -r skill_md; do
    name="$(skill_name "$skill_md")"
    [[ "$name" =~ $valid_name ]] && [ ! -e "$src/$name" ] || continue
    mv "$(dirname "$skill_md")" "$src/$name" || { rm -rf "$tmp"; return 1; }
    SKILL_NAMES+=("$name")
  done < <(find "$tmp"/*/skills -type f -name SKILL.md 2>/dev/null | sort)
  if [ "${#SKILL_NAMES[@]}" -eq 0 ]; then rm -rf "$tmp"; return 1; fi
  SKILL_DESTS=()
  while IFS= read -r dest; do SKILL_DESTS+=("$dest"); done < <(skill_destinations)
  for dest in "${SKILL_DESTS[@]}"; do
    mkdir -p "$dest" || { rm -rf "$tmp"; return 1; }
    for name in "${SKILL_NAMES[@]}"; do
      rm -rf "${dest:?}/${name:?}" || { rm -rf "$tmp"; return 1; }
      cp -R "$src/$name" "$dest/$name" || { rm -rf "$tmp"; return 1; }
    done
  done
  rm -rf "$tmp"
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

SKILL_NAMES=(); SKILL_DESTS=()
SKILLS_INSTALLED=0
if [ "$ZENML_INSTALL_SKIP_SKILLS" = "1" ]; then
  note "Skipping skills (--no-skills)"
else
  step "Installing ZenML agent skills ($ZENML_INSTALL_SKILLS_REPO)"
  if install_skills; then
    ok "${#SKILL_NAMES[@]} skills installed into ${SKILL_DESTS[*]}"
    SKILLS_INSTALLED=1
  else
    warn "Could not install skills. Later: npx skills add $ZENML_INSTALL_SKILLS_REPO"
  fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
say ""
say "${C_GREEN}◆${C_RESET} ${C_BOLD}ZenML is installed.${C_RESET}"
say ""
# In project mode zenml is not on PATH; every command goes through uv run.
# The command the printed steps start with may not be reachable from the
# user's shell yet: a uv this script just installed, or a tool dir that shell
# has never seen. `uvx zenml` is no way around that, since uvx sits in the
# same new directory, so print the one export that fixes this shell (new
# terminals pick up the rc-file change on their own).
# NEEDED_DIR is where the first word of $Z lives, or empty when the user's
# shell already finds it.
if [ "$ZENML_INSTALL_SCOPE" = "project" ]; then
  Z="uv run zenml"; NEEDED_DIR="$(dirname "$UV")"
  PATH="$ORIG_PATH" have uv && NEEDED_DIR=""
  say "  Installed into this project's environment, so run it as ${C_BOLD}uv run zenml ...${C_RESET}"
  say "  (or activate $VENV_DIR)."
  say ""
else
  Z="zenml"; NEEDED_DIR="$TOOL_BIN"
  [ "$ZENML_ON_ORIG_PATH" = "1" ] && NEEDED_DIR=""
fi
if [ -n "$NEEDED_DIR" ]; then
  case "$NEEDED_DIR" in
    "$HOME"/*) NEEDED_DIR="\$HOME${NEEDED_DIR#"$HOME"}" ;;
  esac
  say "  '${Z%% *}' is not on this shell's PATH yet. Open a new terminal, or run:"
  say "    ${C_BOLD}export PATH=\"$NEEDED_DIR:\$PATH\"${C_RESET}"
  say ""
fi
case ",$ZENML_INSTALL_EXTRAS," in
  *,server,*)
    say "  Next, pick where your ZenML server lives:"
    say ""
    if [ "$IS_WINDOWS" = "1" ]; then
      # The local server cannot run as a background process on Windows.
      say "    ${C_BOLD}$Z login --local --blocking${C_RESET}    local, in this terminal. Free, open source."
    else
      say "    ${C_BOLD}$Z login --local${C_RESET}    local, on this machine. Free, open source."
    fi
    say "    ${C_BOLD}$Z login${C_RESET}            ZenML Pro, managed."
    if [ "$OS" = "Darwin" ]; then
      say ""
      say "  On macOS the local server refuses to start without this (add it to your"
      say "  shell profile to keep it):"
      say "    ${C_BOLD}export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES${C_RESET}"
    fi
    ;;
  *)
    say "  Next, connect to a ZenML server:"
    say ""
    say "    ${C_BOLD}$Z login${C_RESET}               ZenML Pro, managed."
    say "    ${C_BOLD}$Z login <url>${C_RESET}         a self-hosted server."
    say ""
    say "  For the local dashboard, re-run this installer with ${C_BOLD}--extras=server${C_RESET}."
    ;;
esac
if [ "$SKILLS_INSTALLED" = "1" ]; then
  say ""
  say "  Then, in your project, tell your coding agent:"
  say "    ${C_BOLD}Use zenml-quick-wins to find improvements in this project.${C_RESET}"
fi
if [ "$ZENML_INSTALL_SCOPE" = "global" ]; then
  say ""
  say "  Pipelines import ZenML, so they need it inside their own project:"
  say "  re-run this installer from that repo, or ${C_BOLD}uv add \"$SPEC\"${C_RESET} there."
fi
say ""
if [ "$SKILLS_INSTALLED" = "1" ]; then
  say "  No pipeline yet?  ${C_BOLD}Use zenml-pipeline-authoring to write my first pipeline.${C_RESET}"
fi
say "  Check setup:      $Z status"
say "  Docs:             https://docs.zenml.io"
say ""
}

main "$@"
