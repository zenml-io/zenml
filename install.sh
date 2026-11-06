#!/usr/bin/env bash
# install.sh — one-line installer for ZenML and Kitaru.
#
#   curl -fsSL https://zenml.io/install | bash
#   curl -fsSL https://zenml.io/install | bash -s -- --products=zenml,kitaru
#
# Asks which products to install, then runs each product's own installer:
# https://zenml.io/install-zenml (install-zenml.sh in this repository) and
# https://zenml.io/install-kitaru (install.sh in zenml-io/kitaru). Those two
# stay the way to install one product without being asked anything, and they
# take the product-specific options (--version, --server, --with, ...).
#
# Without a terminal to ask on (CI, Docker builds, coding agents) it does not
# guess: pass --products. The flags both installers share are passed on.

# Bash-only, but fail politely under sh/dash/zsh-as-sh. This line is POSIX so
# it runs before the shell reaches any bash syntax below.
if [ -z "${BASH_VERSION:-}" ]; then echo "This installer needs bash. Run: curl -fsSL https://zenml.io/install | bash" >&2; exit 1; fi
# macOS /bin/sh is bash in POSIX mode, which the installers it runs reject.
case ":${SHELLOPTS:-}:" in *:posix:*) echo "This installer needs bash, not sh. Run: curl -fsSL https://zenml.io/install | bash" >&2; exit 1 ;; esac

set -euo pipefail

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
ZENML_INSTALL_PRODUCTS="${ZENML_INSTALL_PRODUCTS:-}"       # zenml, kitaru or zenml,kitaru
# Where each product's installer comes from. A local path is used as is, for
# testing a checkout.
ZENML_INSTALL_ZENML_URL="${ZENML_INSTALL_ZENML_URL:-https://zenml.io/install-zenml}"
ZENML_INSTALL_KITARU_URL="${ZENML_INSTALL_KITARU_URL:-https://zenml.io/install-kitaru}"
SHARED_ARGS=()                                              # passed on to each installer
QUIET=0

usage() {
  cat <<'USAGE'
Usage: install.sh [options]

  --products=LIST     What to install: zenml, kitaru, or zenml,kitaru.
                      Asked for when there is a terminal and this is not set.
  --zenml, --kitaru   Shorthands that add one product each

Passed on to each installer:
  --project / --global, --pre, --no-skills, --no-modify-path, --quiet, --verbose

For product-specific options, use that product's installer directly:
  curl -fsSL https://zenml.io/install-zenml | bash -s -- --help
  curl -fsSL https://zenml.io/install-kitaru | bash -s -- --help

Environment equivalents: ZENML_INSTALL_PRODUCTS, NO_COLOR.
USAGE
}

add_products() { ZENML_INSTALL_PRODUCTS="${ZENML_INSTALL_PRODUCTS:+$ZENML_INSTALL_PRODUCTS,}$1"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --products=*) ZENML_INSTALL_PRODUCTS="${1#*=}" ;;
    --products) shift; ZENML_INSTALL_PRODUCTS="${1:-}" ;;
    --zenml) add_products zenml ;;
    --kitaru) add_products kitaru ;;
    --project|--global|--pre|--no-skills|--no-modify-path|--verbose) SHARED_ARGS+=("$1") ;;
    --quiet) SHARED_ARGS+=("$1"); QUIET=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
C_PURPLE=""; C_RED=""; C_DIM=""; C_BOLD=""; C_RESET=""
if [ -z "${NO_COLOR:-}" ] && [ -t 1 ]; then
  C_PURPLE=$'\033[38;5;99m'; C_RED=$'\033[31m'
  C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
fi

say()  { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }
die()  { printf '%s✕%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

fetch_to_file() {
  case "$1" in
    https://*)
      if have curl; then curl -fsSL --proto '=https' --tlsv1.2 -o "$2" "$1"
      else wget -q --https-only -O "$2" "$1"; fi ;;
    *) cp "$1" "$2" ;;
  esac
}

# The question goes to the terminal itself: under `curl | bash` stdin is this
# script, and stdout may be piped into a log.
can_ask() { { : </dev/tty; } 2>/dev/null; }

ask_products() {
  local answer
  {
    printf '\n%s◆%s %sWhat would you like to install?%s\n\n' "$C_PURPLE" "$C_RESET" "$C_BOLD" "$C_RESET"
    printf '    1) ZenML    MLOps for reliable AI: pipelines from classical ML to agents\n'
    printf '    2) Kitaru   Insights from your agent'"'"'s traces\n'
    printf '    3) Both\n\n'
  } >/dev/tty
  for _ in 1 2 3; do
    printf '  Choose 1, 2 or 3 %s[1]%s: ' "$C_DIM" "$C_RESET" >/dev/tty
    IFS= read -r answer </dev/tty || answer=""
    case "$answer" in
      ""|1) ZENML_INSTALL_PRODUCTS=zenml; return 0 ;;
      2) ZENML_INSTALL_PRODUCTS=kitaru; return 0 ;;
      3) ZENML_INSTALL_PRODUCTS=zenml,kitaru; return 0 ;;
    esac
  done
  die "No choice made. Pass one with --products=zenml, --products=kitaru or --products=zenml,kitaru."
}

main() {
if ! have curl && ! have wget; then die "Need curl or wget."; fi

if [ -z "$ZENML_INSTALL_PRODUCTS" ]; then
  if can_ask; then
    ask_products
  else
    die "No terminal to ask which product to install. Pass --products=zenml, --products=kitaru or --products=zenml,kitaru, or use https://zenml.io/install-zenml or https://zenml.io/install-kitaru."
  fi
fi

# Validate, drop duplicates, and always run ZenML first, so the order (and the
# environment a project's .venv is created with) does not depend on how the
# products were listed.
WANT_ZENML=0; WANT_KITARU=0
IFS=',' read -r -a requested <<<"$ZENML_INSTALL_PRODUCTS"
for product in "${requested[@]}"; do
  case "$product" in
    zenml) WANT_ZENML=1 ;;
    kitaru) WANT_KITARU=1 ;;
    *) die "Unknown product: '$product'. Choose from zenml and kitaru." ;;
  esac
done

SCRIPT="$(mktemp)"
trap 'rm -f "$SCRIPT"' EXIT
run_installer() {
  local name="$1" url="$2"
  fetch_to_file "$url" "$SCRIPT" || die "Could not download the $name installer from $url"
  # stdin is /dev/null so the installer can never read the rest of this
  # script when it is being piped in from curl.
  bash "$SCRIPT" "${SHARED_ARGS[@]:+${SHARED_ARGS[@]}}" </dev/null \
    || die "The $name installer failed (its message is above)."
}

[ "$WANT_ZENML" = "1" ] && run_installer ZenML "$ZENML_INSTALL_ZENML_URL"
[ "$WANT_KITARU" = "1" ] && run_installer Kitaru "$ZENML_INSTALL_KITARU_URL"
if [ "$WANT_ZENML" = "1" ] && [ "$WANT_KITARU" = "1" ]; then
  say "${C_PURPLE}◆${C_RESET} ${C_BOLD}ZenML and Kitaru are installed.${C_RESET} Each one's next steps are above."
  say ""
fi
}

main "$@"
