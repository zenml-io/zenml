#!/usr/bin/env bash
# install-zenml.sh — one-line ZenML installer.
#
#   curl -fsSL https://raw.githubusercontent.com/zenml-io/zenml/main/install-zenml.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/zenml-io/zenml/main/install-zenml.sh | bash -s -- --server=https://zenml.example.com
#
# The install.sh menu asks whether to install ZenML, Kitaru or both, and
# runs this script for ZenML.
#
# What it does, in order:
#   1. Makes sure `uv` is available (installs it from astral.sh if not).
#   2. Installs zenml[local], which runs pipelines without a server. Where
#      depends on where you run it:
#        - inside a Python project (pyproject.toml or uv.lock in the current
#          directory): `uv add` into that project's environment, because your
#          pipelines import ZenML and have to run next to their own
#          dependencies;
#        - anywhere else: `uv tool install` into an isolated environment, with
#          `zenml` on PATH (~/.local/bin). Good for logging in, managing
#          stacks and browsing runs; running pipelines needs the project form.
#      --project / --global force either.
#   3. Installs the ZenML agent skills (zenml-io/skills) into ~/.agents/skills,
#      plus ~/.claude/skills when Claude Code is installed.
#   4. Stops there and prints how to get a server: local in Docker
#      (`zenml login --local --docker`) or ZenML Pro (`zenml login`), or
#      `zenml login <url>` for a server passed with --server. Login is a
#      decision, so the script does not make it for you.
#
# Nothing here needs sudo. Re-running upgrades ZenML within configured version
# constraints and adds missing skills; existing skill paths are preserved.
#
# Kept parallel to Kitaru's installer (zenml-io/kitaru, install.sh). Kitaru's
# also registers an MCP server; this one does not yet.

# Bash-only, but fail politely under sh/dash/zsh-as-sh. This line is POSIX so
# it runs before the shell reaches any bash syntax below.
if [ -z "${BASH_VERSION:-}" ]; then echo "ZenML's installer needs bash. Run: curl -fsSL https://raw.githubusercontent.com/zenml-io/zenml/main/install-zenml.sh | bash" >&2; exit 1; fi
# macOS /bin/sh is bash in POSIX mode: BASH_VERSION is set, but POSIX mode
# rejects the process substitutions below with a bare syntax error.
case ":${SHELLOPTS:-}:" in *:posix:*) echo "ZenML's installer needs bash, not sh. Run: curl -fsSL https://raw.githubusercontent.com/zenml-io/zenml/main/install-zenml.sh | bash" >&2; exit 1 ;; esac

set -euo pipefail

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
# ZENML_INSTALL_* rather than ZENML_*: the ZenML runtime reads ZENML_*
# variables itself (ZENML_VERSION among them), and these are not for it.
ZENML_INSTALL_RECONFIGURE=0
if [ "${ZENML_INSTALL_EXTRAS+x}" = "x" ] || [ -n "${ZENML_INSTALL_VERSION:-}${ZENML_INSTALL_PYTHON:-}${UV_PYTHON:-}" ] || [ "${ZENML_INSTALL_PRE:-0}" = "1" ]; then
  ZENML_INSTALL_RECONFIGURE=1
fi
ZENML_INSTALL_VERSION="${ZENML_INSTALL_VERSION:-}"          # pin, e.g. 0.98.1
ZENML_INSTALL_PRE="${ZENML_INSTALL_PRE:-0}"                 # allow pre-releases
ZENML_INSTALL_EXTRAS="${ZENML_INSTALL_EXTRAS-local}"        # empty = base package
ZENML_INSTALL_SERVER="${ZENML_INSTALL_SERVER:-}"            # a server to log in to next
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
ZENML_INSTALL_MIN_UV="0.13.4"                               # tested project Python-range resolution

usage() {
  cat <<'USAGE'
Usage: install-zenml.sh [options]

  --version=X.Y.Z     Install a specific ZenML version (default: >=0.98.1)
  --pre               Allow pre-release versions
  --extras=LIST       ZenML extras, comma-separated (default: local, which
                      runs pipelines without a server). --extras=server also
                      runs the local server without Docker; --extras= installs
                      the base package, enough to connect to a deployed server.
  --server=URL        Your ZenML server (self-hosted or a ZenML Pro workspace);
                      the next steps then say to log in there
  --with=PKG          Also install PKG into the same environment (repeatable),
                      e.g. --with=scikit-learn
  --project           Install into the Python project in the current directory
                      (uv add). Default when a pyproject.toml or uv.lock is here.
  --global            Install into an isolated uv tool environment on PATH.
                      Default anywhere else.
  --python=X.Y        Python for the new environment (default: 3.12 for the
                      isolated one; in a project without a pinned Python, the
                      newest one both the project and ZenML support)
  --no-skills         Skip adding coding-agent skills (existing paths are kept)
  --no-modify-path    Do not edit shell rc files; print the needed PATH change
  --quiet             Only print errors
  --verbose           Print every command
  -h, --help          This text

Environment equivalents: ZENML_INSTALL_VERSION, ZENML_INSTALL_PRE=1,
ZENML_INSTALL_EXTRAS, ZENML_INSTALL_SERVER, ZENML_INSTALL_SCOPE=project|global,
ZENML_INSTALL_PYTHON, ZENML_INSTALL_SKIP_SKILLS=1,
ZENML_INSTALL_NO_MODIFY_PATH=1, ZENML_INSTALL_QUIET=1,
ZENML_INSTALL_VERBOSE=1, NO_COLOR.

The installer reports one anonymous usage event when it finishes. Set
ZENML_ANALYTICS_OPT_IN=false or DO_NOT_TRACK=1 to turn that off.
USAGE
}

require_value() {
  if [ "$#" -lt 2 ] || [ -z "$2" ] || [[ "$2" == -* ]]; then
    echo "Option $1 requires a value. Use $1=VALUE (or --extras= for no extras)." >&2
    exit 2
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version=|--server=|--python=|--with=) echo "Option ${1%=} requires a value." >&2; exit 2 ;;
    --version=*) ZENML_INSTALL_VERSION="${1#*=}"; ZENML_INSTALL_RECONFIGURE=1 ;;
    --version) require_value "$@"; shift; ZENML_INSTALL_VERSION="$1"; ZENML_INSTALL_RECONFIGURE=1 ;;
    --pre) ZENML_INSTALL_PRE=1; ZENML_INSTALL_RECONFIGURE=1 ;;
    --extras=*) ZENML_INSTALL_EXTRAS="${1#*=}"; ZENML_INSTALL_RECONFIGURE=1 ;;
    --extras) require_value "$@"; shift; ZENML_INSTALL_EXTRAS="$1"; ZENML_INSTALL_RECONFIGURE=1 ;;
    --server=*) ZENML_INSTALL_SERVER="${1#*=}" ;;
    --server) require_value "$@"; shift; ZENML_INSTALL_SERVER="$1" ;;
    --with=*) ZENML_INSTALL_WITH+=("${1#*=}"); ZENML_INSTALL_RECONFIGURE=1 ;;
    --with) require_value "$@"; shift; ZENML_INSTALL_WITH+=("$1"); ZENML_INSTALL_RECONFIGURE=1 ;;
    --python=*) ZENML_INSTALL_PYTHON="${1#*=}"; ZENML_INSTALL_RECONFIGURE=1 ;;
    --python) require_value "$@"; shift; ZENML_INSTALL_PYTHON="$1"; ZENML_INSTALL_RECONFIGURE=1 ;;
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
  if [ "$status" -ne 0 ]; then cat "$out" >&2
  else grep -i '^warning:' "$out" >&2 || true; fi
  rm -f "$out"; return "$status"
}
have() { command -v "$1" >/dev/null 2>&1; }

# Usage analytics: after the install, the ZenML CLI reports one anonymous
# "installed with the script" event, the same way it reports other usage.
# ZenML's own opt-out switch and DO_NOT_TRACK both turn it off.
analytics_opted_out() {
  case "$(printf '%s' "${ZENML_ANALYTICS_OPT_IN:-}" | tr '[:upper:]' '[:lower:]')" in
    0|false|no|off|n|f) return 0 ;;
  esac
  case "$(printf '%s' "${DO_NOT_TRACK:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes) return 0 ;;
  esac
  return 1
}
# The report runs in the background so a slow network never holds up the
# install. Its first run also sets up ZenML's local database, so the script
# gives it a few seconds to finish before handing the terminal back: that
# keeps it from overlapping with the user's first zenml command. A ZenML
# version without the command (an older pin) fails silently.
REPORT_PID=""
report_install() {
  if analytics_opted_out; then return 0; fi
  "$ZENML_BIN" analytics report-install --scope "$ZENML_INSTALL_SCOPE" >/dev/null 2>&1 </dev/null &
  REPORT_PID=$!
}
wait_for_report() {
  local tries=0
  [ -n "$REPORT_PID" ] || return 0
  while [ "$tries" -lt 50 ] && kill -0 "$REPORT_PID" 2>/dev/null; do
    sleep 0.2; tries=$((tries + 1))
  done
  return 0
}
# A next-step command padded to $1 columns, then what it is for.
say_cmd() { [ "$ZENML_INSTALL_QUIET" = "1" ] || printf '    %s%-*s%s    %s\n' "$C_BOLD" "$1" "$2" "$C_RESET" "$3"; }

main() {
# PATH as the user had it, before this script adds anything to it.
ORIG_PATH="$PATH"
INSTALL_TMP="$(mktemp -d)"
trap 'rm -rf "$INSTALL_TMP"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
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

have curl || die "Need curl with HTTPS support. Install curl with your system package manager and re-run."

fetch_to_stdout() {
  curl -fsSL --proto '=https' --proto-redir '=https' --tlsv1.2 "$1"
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
  trap 'rm -f "$UV_INSTALLER"; rm -rf "${INSTALL_TMP:-}"' EXIT
  fetch_to_stdout https://astral.sh/uv/install.sh >"$UV_INSTALLER" \
    || die "Could not download the uv installer from https://astral.sh/uv/install.sh"
  if [ "$ZENML_INSTALL_NO_MODIFY_PATH" = "1" ]; then
    export UV_NO_MODIFY_PATH=1
  fi
  quiet env PATH="$ORIG_PATH" sh "$UV_INSTALLER" --quiet \
    || die "uv install failed. Install it from https://docs.astral.sh/uv/ and re-run."
  rm -f "$UV_INSTALLER"; trap 'rm -rf "${INSTALL_TMP:-}"' EXIT
  # Use the binary we just installed by absolute path, and put its directory
  # in front so an older uv earlier on PATH (or bash's hashed path) can't win.
  UV_DIR="${UV_INSTALL_DIR:-${CARGO_DIST_FORCE_INSTALL_DIR:-${UV_UNMANAGED_INSTALL:-${XDG_BIN_HOME:-${XDG_DATA_HOME:+$XDG_DATA_HOME/../bin}}}}}"
  UV_DIR="${UV_DIR:-$HOME/.local/bin}"
  if [ "$UV_DIR" = "${CARGO_HOME:-$HOME/.cargo}" ]; then UV_DIR="$UV_DIR/bin"; fi
  UV_DIR="$(cd "$UV_DIR" && pwd)" || die "Could not locate uv's install directory."
  UV="$UV_DIR/uv"
  ensure_path "$UV_DIR"; hash -r
  [ -x "$UV" ] || die "uv installed but $UV is missing. Install it from https://docs.astral.sh/uv/ and re-run."
  version_ge "$(uv_version_of "$UV")" "$ZENML_INSTALL_MIN_UV" \
    || die "uv at $UV is $(uv_version_of "$UV"), older than $ZENML_INSTALL_MIN_UV. Install a current uv and re-run."
  ok "uv $(uv_version_of "$UV") installed"
}

# $UV is the uv binary used for everything below (absolute path).
UV=""
if have uv; then
  UV="$(command -v uv)"
  UV_VER="$(uv_version_of "$UV" || true)"
  if [ -n "$UV_VER" ] && version_ge "$UV_VER" "$ZENML_INSTALL_MIN_UV"; then
    ok "uv $UV_VER found"
  else
    note "uv at $UV is unavailable or older than $ZENML_INSTALL_MIN_UV; installing a current one."
    install_uv
  fi
else
  install_uv
fi

persist_path() {
  # `uv tool update-shell` handles bash/zsh/fish when it recognizes the login
  # shell. Cover the rest (Alpine sh, containers, CI images) by appending to
  # the active login profile when uv does not edit the shell configuration.
  local dir="$1" f profile="$HOME/.profile"
  case "${SHELL:-bash}" in
    */bash|bash)
      # Bash skips .profile when a readable .bash_profile or .bash_login exists.
      for f in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do
        if [ -f "$f" ] && [ -r "$f" ]; then profile="$f"; break; fi
      done
      [ -f "$profile" ] && grep -Fqs "$dir" "$profile" && return 0 ;;
    *)
      for f in "$HOME/.bashrc" "$HOME/.zshenv" "$HOME/.zshrc" "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.config/fish/config.fish"; do
        [ -f "$f" ] && grep -Fqs "$dir" "$f" && return 0
      done ;;
  esac
  # shellcheck disable=SC2016  # $PATH must stay literal: it expands at shell startup.
  if ! printf '\n# Added by the ZenML installer\nexport PATH="%s:$PATH"\n' "$dir" >> "$profile"; then
    warn "Could not update $profile. Add this to your shell profile: export PATH=\"$dir:\$PATH\""
  fi
  return 0
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
if [ -n "$ZENML_INSTALL_VERSION" ]; then SPEC="${SPEC}==${ZENML_INSTALL_VERSION}"
else SPEC="${SPEC}>=0.98.1"; fi
EXTRA_PKGS=()
for pkg in "${ZENML_INSTALL_WITH[@]:-}"; do [ -n "$pkg" ] && EXTRA_PKGS+=("$pkg"); done

# TOML is parsed by the standard library; uv interprets the combined PEP 440
# requirement through script metadata. No project code or dependency is run.
prepare_project_python() {
  local parser
  parser="$(VIRTUAL_ENV="" "$UV" python find --no-project '>=3.11,<3.15' 2>/dev/null || true)"
  if [ -z "$parser" ]; then
    quiet "$UV" python install --no-bin '>=3.11,<3.15' \
      || die "Could not get Python >=3.11,<3.15 to read project metadata. Install a supported Python with uv and re-run."
    parser="$(VIRTUAL_ENV="" "$UV" python find --no-project '>=3.11,<3.15')"
  fi
  [ "$IS_WINDOWS" = "0" ] || parser="$(cygpath -u "$parser")"
  "$parser" -I - "$PROJECT_DIR" "$PROJECT_PYTHON_SCRIPT" "$ZENML_SUPPORTED_PYTHON" <<'PY'
import json
import os
from pathlib import Path
import sys
import tomllib


def load(path: Path) -> dict:
    with (path / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


try:
    current = Path(sys.argv[1]).resolve()
    data = load(current)
    root = current
    projects = [(current, data)]
    for candidate in (current, *current.parents):
        if not (candidate / "pyproject.toml").is_file():
            continue
        parent = load(candidate)
        workspace = parent.get("tool", {}).get("uv", {}).get("workspace")
        if workspace is None:
            continue
        excluded = {p.resolve() for pattern in workspace.get("exclude", []) for p in candidate.glob(pattern)}
        members = {p.resolve() for pattern in workspace.get("members", []) for p in candidate.glob(pattern)} - excluded
        if current != candidate and current not in members:
            continue
        root = candidate
        projects = [(p, load(p)) for p in sorted(members | {candidate}) if (p / "pyproject.toml").is_file()]
        break
    for path, metadata in projects:
        foreign = set(metadata.get("tool", {})) & {"poetry", "pdm", "pipenv"}
        foreign.update(name for name in ("poetry.lock", "pdm.lock", "Pipfile", "Pipfile.lock") if (path / name).exists())
        if foreign:
            raise ValueError(f"{path} uses {', '.join(sorted(foreign))}. Add ZenML with that project's package manager, or explicitly migrate it to uv before using --project. Use --global only for a separate CLI installation.")
    if "project" not in data:
        raise ValueError(f"{current}/pyproject.toml has no [project] metadata. Run this installer from a Python project/workspace member, initialize one with uv init, or use --global for a separate CLI installation.")
    requirements = [sys.argv[3]]
    for _, metadata in projects:
        requirement = metadata.get("project", {}).get("requires-python")
        if requirement:
            requirements.append(requirement)
    Path(sys.argv[2]).write_text("# /// script\n# requires-python = " + json.dumps(",".join(requirements)) + "\n# ///\n")
    environment = Path(os.environ.get("UV_PROJECT_ENVIRONMENT", ".venv"))
    if not environment.is_absolute():
        environment = root / environment
    Path(sys.argv[2] + ".environment").write_text(str(environment))
except (OSError, ValueError, TypeError) as error:
    print(f"Cannot install into this project: {error}", file=sys.stderr)
    sys.exit(1)
PY
}

find_requested_python() {
  local request="$1" selected
  selected="$(VIRTUAL_ENV="" "$UV" python find --no-project "$request" 2>/dev/null || true)"
  if [ -z "$selected" ]; then
    quiet "$UV" python install --no-bin "$request" || return 1
    selected="$(VIRTUAL_ENV="" "$UV" python find --no-project "$request")" || return 1
  fi
  [ "$IS_WINDOWS" = "0" ] || selected="$(cygpath -u "$selected")"
  printf '%s\n' "$selected"
}

validate_python() {
  "$1" -I -c 'import sys; sys.exit(not ((3, 10) <= sys.version_info[:2] < (3, 15)))' \
    || die "Selected Python at $1 is unsupported. ZenML needs Python $ZENML_SUPPORTED_PYTHON. Choose a compatible interpreter with --python, or update your project's Python pin/environment explicitly."
}

PROJECT_DIR="$PWD"
if [ "$ZENML_INSTALL_SCOPE" = "auto" ]; then
  if [ -f "$PROJECT_DIR/pyproject.toml" ] || [ -f "$PROJECT_DIR/uv.lock" ] || [ -f "$PROJECT_DIR/Pipfile" ] || [ -f "$PROJECT_DIR/Pipfile.lock" ] || [ -f "$PROJECT_DIR/poetry.lock" ] || [ -f "$PROJECT_DIR/pdm.lock" ]; then
    ZENML_INSTALL_SCOPE=project
  else
    ZENML_INSTALL_SCOPE=global
  fi
fi
case "$ZENML_INSTALL_SCOPE" in project|global) ;; *) die "Unknown installation scope: $ZENML_INSTALL_SCOPE (use project or global)." ;; esac

if [ "$ZENML_INSTALL_SCOPE" = "project" ]; then
  # ---- into the project in the current directory ---------------------------
  # Pipelines import ZenML, so it has to live where the pipelines'
  # dependencies live. `uv add` puts zenml into this project's environment
  # (creating .venv if needed) and records it in pyproject.toml.
  [ -f "$PROJECT_DIR/pyproject.toml" ] || die "Project mode needs a pyproject.toml with [project] metadata in $PROJECT_DIR. An orphan uv.lock or Pipfile is not a uv project; use its package manager, run \`uv init\` explicitly, or choose --global for a separate CLI."
  step "Installing $SPEC into this project ($PROJECT_DIR)"
  # A plain `uv add` keeps an already-locked zenml at its old version;
  # --upgrade-package is what makes re-running the installer an upgrade.
  UV_ADD=(add)
  [ "$ZENML_INSTALL_PRE" = "1" ] && UV_ADD+=(--prerelease allow)
  PROJECT_PYTHON_SCRIPT="$INSTALL_TMP/project-python.py"
  prepare_project_python || die "Project metadata validation failed; no dependencies were changed."
  PROJECT_ENVIRONMENT="$(cat "$PROJECT_PYTHON_SCRIPT.environment")"
  [ "$IS_WINDOWS" = "0" ] || PROJECT_ENVIRONMENT="$(cygpath -u "$PROJECT_ENVIRONMENT")"
  PYTHON_REQUEST="${ZENML_INSTALL_PYTHON:-${UV_PYTHON:-}}"
  if [ -z "$PYTHON_REQUEST" ]; then PYTHON_REQUEST="$("$UV" python pin 2>/dev/null || true)"; fi
  if [ -n "$PYTHON_REQUEST" ]; then
    PROJECT_PYTHON="$(find_requested_python "$PYTHON_REQUEST")" \
      || die "Could not find the selected Python ($PYTHON_REQUEST). Choose a supported interpreter with --python."
  elif [ -f "$PROJECT_ENVIRONMENT/pyvenv.cfg" ]; then
    if [ "$IS_WINDOWS" = "1" ]; then PROJECT_PYTHON="$PROJECT_ENVIRONMENT/Scripts/python.exe"
    else PROJECT_PYTHON="$PROJECT_ENVIRONMENT/bin/python"; fi
  else
    PROJECT_PYTHON="$(VIRTUAL_ENV="" "$UV" python find --script "$PROJECT_PYTHON_SCRIPT" 2>/dev/null || true)"
    if [ -z "$PROJECT_PYTHON" ]; then
      quiet "$UV" python install --no-bin "$(sed -n 's/^# requires-python = "\(.*\)"$/\1/p' "$PROJECT_PYTHON_SCRIPT")" \
        || die "No Python satisfies both this project's requirements and ZenML's $ZENML_SUPPORTED_PYTHON. Update the project's requirements explicitly or use --global for a separate CLI."
      PROJECT_PYTHON="$(VIRTUAL_ENV="" "$UV" python find --script "$PROJECT_PYTHON_SCRIPT")"
    fi
  fi
  [ "$IS_WINDOWS" = "0" ] || PROJECT_PYTHON="$(cygpath -u "$PROJECT_PYTHON")"
  validate_python "$PROJECT_PYTHON"
  # An exact-version intersection checks configured interpreters against all
  # workspace requirements before uv add can change dependencies.
  PYTHON_VERSION="$("$PROJECT_PYTHON" -I -c 'import platform; print(platform.python_version())')"
  printf '# /// script\n# requires-python = "%s,==%s"\n# ///\n' \
    "$(sed -n 's/^# requires-python = "\(.*\)"$/\1/p' "$PROJECT_PYTHON_SCRIPT")" "$PYTHON_VERSION" > "$INSTALL_TMP/selected-python.py"
  PATH="$(dirname "$PROJECT_PYTHON"):$PATH" VIRTUAL_ENV="" "$UV" python find --no-python-downloads --script "$INSTALL_TMP/selected-python.py" >/dev/null \
    || die "Selected Python $PYTHON_VERSION does not satisfy this project's requirements. Update its Python pin/environment explicitly, or choose --python."
  if [ -n "${VIRTUAL_ENV:-}" ] && [ "$VIRTUAL_ENV" != "$PROJECT_ENVIRONMENT" ]; then
    warn "The active environment $VIRTUAL_ENV is not this project's environment ($PROJECT_ENVIRONMENT); uv will use the project environment."
  fi
  PROJECT_SPEC="$SPEC"
  if [ -z "$ZENML_INSTALL_VERSION" ]; then
    PROJECT_SPEC="zenml"
    [ -n "$ZENML_INSTALL_EXTRAS" ] && PROJECT_SPEC="zenml[$ZENML_INSTALL_EXTRAS]"
    UV_ADD+=(--upgrade-package 'zenml>=0.98.1')
  else
    UV_ADD+=(--upgrade-package zenml)
  fi
  UV_ADD+=(--python "$PROJECT_PYTHON")
  for pkg in "${EXTRA_PKGS[@]:+${EXTRA_PKGS[@]}}"; do UV_ADD+=(--upgrade-package "$pkg"); done
  quiet "$UV" "${UV_ADD[@]}" "$PROJECT_SPEC" "${EXTRA_PKGS[@]:+${EXTRA_PKGS[@]}}" \
    || die "Combined dependency resolution failed (uv's message is above). Check ZenML, project constraints, and any --with packages together; ZenML supports Python $ZENML_SUPPORTED_PYTHON, and Kitaru needs Python >=3.11 when requested."
  # Ask uv for the environment it just installed into. No sync, package
  # resolution, or Python downloads may happen during this verification.
  VENV_DIR="$("$UV" run --python "$PROJECT_PYTHON" --no-sync --offline --no-python-downloads python -c 'import sys; print(sys.prefix)')" \
    || die "Could not locate the project environment after uv add. Re-run with --verbose."
  [ "$IS_WINDOWS" = "1" ] && VENV_DIR="$(cygpath -u "$VENV_DIR")"
  if [ "$IS_WINDOWS" = "1" ]; then TOOL_BIN="$VENV_DIR/Scripts"; else TOOL_BIN="$VENV_DIR/bin"; fi
  ZENML_BIN="$TOOL_BIN/zenml"
  [ -x "$ZENML_BIN" ] || [ -x "$ZENML_BIN.exe" ] || die "uv reported success but $ZENML_BIN is missing. Re-run with --verbose."
  ZENML_VERSION="$(zenml_version_of "$ZENML_BIN")" || die "ZenML was installed but its CLI could not start. Run $ZENML_BIN --version for details."
  ok "zenml $ZENML_VERSION installed into this project's environment"
  note "environment: $VENV_DIR (recorded in pyproject.toml)"
  PROJECT_COMMAND="uv run zenml"
  if [ -n "$ZENML_INSTALL_PYTHON" ] || [ -n "${UV_PYTHON:-}" ]; then
    printf -v PROJECT_PYTHON_ARG '%q' "$PROJECT_PYTHON"
    PROJECT_COMMAND="uv run --python $PROJECT_PYTHON_ARG zenml"
    note "Your Python pin was left unchanged; keep --python when running uv if it differs."
  fi
  note "run it as: $PROJECT_COMMAND ...   (or activate the environment)"
else
  # ---- isolated tool environment on PATH -----------------------------------
  TOOL_BIN="$("$UV" tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
  TOOL_ENV="$("$UV" tool dir 2>/dev/null || echo "$HOME/.local/share/uv/tools")/zenml"
  if [ "$IS_WINDOWS" = "1" ]; then
    TOOL_BIN="$(cygpath -u "$TOOL_BIN")"
    TOOL_ENV="$(cygpath -u "$TOOL_ENV")"
  fi
  if [ -f "$TOOL_ENV/uv-receipt.toml" ] && [ "$ZENML_INSTALL_RECONFIGURE" = "0" ]; then
    if [ "$IS_WINDOWS" = "1" ]; then TOOL_PYTHON="$TOOL_ENV/Scripts/python.exe"
    else TOOL_PYTHON="$TOOL_ENV/bin/python"; fi
    validate_python "$TOOL_PYTHON"
    step "Upgrading ZenML within its configured constraints (preserving extras, added packages, and Python)"
    quiet "$UV" tool upgrade 'zenml>=0.98.1' \
      || die "uv tool upgrade failed. Existing tool settings were retained; check its version constraints and added packages. Re-run with --verbose for details."
  else
    TOOL_PYTHON="$(find_requested_python "${ZENML_INSTALL_PYTHON:-${UV_PYTHON:-3.12}}")" \
      || die "Could not find the requested Python. Choose a supported interpreter with --python."
    validate_python "$TOOL_PYTHON"
    UV_ARGS=(tool install --upgrade --python "$TOOL_PYTHON")
    [ "$ZENML_INSTALL_PRE" = "1" ] && UV_ARGS+=(--prerelease allow)
    for pkg in "${EXTRA_PKGS[@]:+${EXTRA_PKGS[@]}}"; do UV_ARGS+=(--with "$pkg"); done
    if [ -e "$TOOL_BIN/zenml" ] && [ ! -f "$TOOL_ENV/uv-receipt.toml" ]; then
      warn "$TOOL_BIN/zenml already exists outside uv's ZenML tool. Remove it with its original package manager (pip/pipx), or choose a different UV_TOOL_BIN_DIR; this installer will not force replacement."
    fi
    step "Installing $SPEC (isolated, on PATH)"
    [ ! -f "$TOOL_ENV/uv-receipt.toml" ] || note "Explicit package/Python options reconfigure the existing tool; include every extra and --with package you want to keep."
    quiet "$UV" "${UV_ARGS[@]}" "$SPEC" \
      || die "Combined tool dependency resolution failed (uv's message is above). Check ZenML and any --with packages together; ZenML needs Python $ZENML_SUPPORTED_PYTHON, and Kitaru needs >=3.11 when requested. An unmanaged executable must be removed with its original package manager before retrying."
  fi

  # uv puts tool executables in its tool bin dir; make sure future shells see it.
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
  ZENML_VERSION="$(zenml_version_of "$ZENML_BIN")" || die "ZenML was installed but its CLI could not start. Run $ZENML_BIN --version for details."
  if [ -z "$ZENML_INSTALL_VERSION" ] && { ! version_ge "$ZENML_VERSION" '0.98.1' || [[ "$ZENML_VERSION" =~ ^0\.98\.1(a|b|rc|\.dev) ]]; }; then
    die "The existing tool is pinned below the default ZenML floor (0.98.1). Its pin was preserved. Use --version=$ZENML_VERSION to deliberately keep this historical version, or explicitly reconfigure it with --version=<supported-version>."
  fi
  ok "zenml $ZENML_VERSION installed"
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
# Codex reads ~/.agents/skills directly. Claude Code uses its own copy.
skill_destinations() {
  echo "$HOME/.agents/skills"
  if have claude || [ -d "$HOME/.claude" ]; then echo "$HOME/.claude/skills"; fi
}

skill_name() {
  # The `name:` field of a SKILL.md frontmatter block.
  awk 'NR == 1 { if ($0 !~ /^---/) exit; next }
       /^---/ { exit }
       /^name:/ { sub(/\r$/, ""); sub(/^name:[[:space:]]*/, ""); gsub(/["\047]/, ""); print; exit }' "$1"
}

install_skills() {
  local saved_exit saved_int saved_term status=0
  saved_exit="$(trap -p EXIT)"; saved_int="$(trap -p INT)"; saved_term="$(trap -p TERM)"
  SKILLS_TMP="$(mktemp -d)" || return 1
  SKILL_STAGING=""
  trap 'rm -rf "$SKILLS_TMP" "${SKILL_STAGING:-}" "${INSTALL_TMP:-}"' EXIT
  trap 'rm -rf "$SKILLS_TMP" "${SKILL_STAGING:-}"; trap - EXIT; eval "$saved_exit"; exit 130' INT
  trap 'rm -rf "$SKILLS_TMP" "${SKILL_STAGING:-}"; trap - EXIT; eval "$saved_exit"; exit 143' TERM
  copy_skills "$SKILLS_TMP" || status=$?
  rm -rf "$SKILLS_TMP" "${SKILL_STAGING:-}"
  trap - EXIT INT TERM
  eval "$saved_exit"; eval "$saved_int"; eval "$saved_term"
  return "$status"
}

copy_skills() {
  # Fetch the repository tarball (no git, no Node, no auth, nothing executed
  # from the current directory). Re-runs add missing skills and preserve every
  # existing path, including customized skills and symlinks.
  local tmp url src skill_md name dest staging
  SKILLS_ADDED=0; SKILLS_PRESERVED=0
  tmp="$1"
  url="https://github.com/${ZENML_INSTALL_SKILLS_REPO}/archive/refs/heads/main.tar.gz"
  if ! fetch_to_stdout "$url" | tar -xzf - -C "$tmp" 2>/dev/null; then
    rm -rf "$tmp"; return 1
  fi
  # zenml-io/skills is a Claude Code plugin marketplace
  # (skills/<plugin>/skills/<dir>/SKILL.md) whose <dir> names are generic
  # (scoping, quick-wins). Each skill is staged under its frontmatter name
  # instead (zenml-scoping, airflow-to-zenml-migration), and only when that
  # is a plain skill name mentioning zenml, never an arbitrary path.
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
      if [ -e "$dest/$name" ] || [ -L "$dest/$name" ]; then
        SKILLS_PRESERVED=$((SKILLS_PRESERVED + 1))
        continue
      fi
      # Copy on the destination filesystem so publishing the complete directory
      # is a rename. A failed copy can only damage this temporary directory.
      staging="$(mktemp -d "$dest/.zenml-skills.XXXXXX")" || { rm -rf "$tmp"; return 1; }
      SKILL_STAGING="$staging"
      if ! cp -R "$src/$name" "$staging/$name"; then
        rm -rf "$staging" "$tmp"; return 1
      fi
      if [ -e "$dest/$name" ] || [ -L "$dest/$name" ]; then
        SKILLS_PRESERVED=$((SKILLS_PRESERVED + 1))
        rm -rf "$staging"
        continue
      fi
      # -n prevents replacement if a path appears before the rename.
      if ! mv -n "$staging/$name" "$dest/"; then
        rm -rf "$staging" "$tmp"; return 1
      fi
      if [ -e "$staging/$name" ]; then
        SKILLS_PRESERVED=$((SKILLS_PRESERVED + 1))
      else
        SKILLS_ADDED=$((SKILLS_ADDED + 1))
      fi
      rm -rf "$staging"
    done
  done
  rm -rf "$tmp"
  return 0
}

SKILL_NAMES=(); SKILL_DESTS=()
SKILLS_ADDED=0; SKILLS_PRESERVED=0
SKILLS_INSTALLED=0
if [ "$ZENML_INSTALL_SKIP_SKILLS" = "1" ]; then
  note "Skipping skills (--no-skills)"
else
  step "Installing ZenML agent skills ($ZENML_INSTALL_SKILLS_REPO)"
  if install_skills; then
    ok "$SKILLS_ADDED skill copies added; $SKILLS_PRESERVED existing paths preserved in ${SKILL_DESTS[*]}"
    if [ "$SKILLS_ADDED" -gt 0 ] || [ "$SKILLS_PRESERVED" -gt 0 ]; then SKILLS_INSTALLED=1; fi
  else
    warn "Could not install skills. Later: npx skills add $ZENML_INSTALL_SKILLS_REPO"
  fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
report_install
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
  Z="$PROJECT_COMMAND"; NEEDED_DIR="$(dirname "$UV")"
  [ "$(PATH="$ORIG_PATH" command -v uv 2>/dev/null || true)" = "$UV" ] && NEEDED_DIR=""
  say "  Installed into this project's environment, so run it as ${C_BOLD}$Z ...${C_RESET}"
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
# Without the server extra the local server runs in Docker, as Kitaru's does.
# With it, it runs as a background process, which Windows cannot do.
if [[ ",$ZENML_INSTALL_EXTRAS," != *,server,* ]]; then
  LOCAL_CMD="$Z login --local --docker"; LOCAL_NOTE="local, with Docker. Free, open source."
elif [ "$IS_WINDOWS" = "1" ]; then
  LOCAL_CMD="$Z login --local --blocking"; LOCAL_NOTE="local, in this terminal. Free, open source."
else
  LOCAL_CMD="$Z login --local"; LOCAL_NOTE="local, on this machine. Free, open source."
fi
if [ -n "$ZENML_INSTALL_SERVER" ]; then
  say "  Next, log in to your server:"
  say ""
  printf -v SERVER_ARG '%q' "$ZENML_INSTALL_SERVER"
  say "    ${C_BOLD}$Z login $SERVER_ARG${C_RESET}"
else
  say "  Next, pick where your ZenML server lives:"
  say ""
  say_cmd "${#LOCAL_CMD}" "$LOCAL_CMD" "$LOCAL_NOTE"
  say_cmd "${#LOCAL_CMD}" "$Z login" "ZenML Pro, managed."
  if [ "$OS" = "Darwin" ]; then
    say ""
    say "  On macOS the local server refuses to start without this (add it to your"
    say "  shell profile to keep it):"
    say "    ${C_BOLD}export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES${C_RESET}"
  fi
fi
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
if [ -n "$REPORT_PID" ]; then
  note "This install was reported as anonymous usage data. Turn that off with: $Z analytics opt-out"
  note "(or set ZENML_ANALYTICS_OPT_IN=false before installing)."
  say ""
fi
wait_for_report
}

main "$@"
