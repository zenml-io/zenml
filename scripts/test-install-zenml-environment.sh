#!/usr/bin/env bash
# Offline installer regressions using real uv and a minimal fixture wheel.
set -euo pipefail
INSTALLER="${1:-$(cd "$(dirname "$0")/.." && pwd)/install-zenml.sh}"
INSTALLER="$(cd "$(dirname "$INSTALLER")" && pwd)/$(basename "$INSTALLER")"
command -v uv >/dev/null
PYTHON="$(uv python find --no-python-downloads ">=3.11,<3.14")"
TMP="$(mktemp -d)"
TMP="$(cd "$TMP" && pwd -P)"
trap 'rm -rf "$TMP"' EXIT
UV_PYTHON_INSTALL_DIR="$(uv python dir)"
export UV_CACHE_DIR="$TMP/cache" UV_PYTHON_INSTALL_DIR
export UV_TOOL_DIR="$TMP/tools" UV_TOOL_BIN_DIR="$TMP/bin"
export XDG_CONFIG_HOME="$TMP/config" XDG_DATA_HOME="$TMP/data"
export XDG_CACHE_HOME="$TMP/xdg-cache" ZENML_CONFIG_PATH="$TMP/zenml"
# Test installs must never report usage.
export ZENML_ANALYTICS_OPT_IN=false
export UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never UV_NO_CONFIG=1
export UV_NO_INDEX=1 UV_FIND_LINKS="$TMP/wheels"
unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_PYTHON UV_PROJECT UV_WORKING_DIR UV_CONSTRAINT UV_FROZEN UV_NO_SYNC
mkdir -p "$TMP/wheels"
# This is an installer fixture, not a test of the real ZenML package.
"$PYTHON" - "$TMP/wheels" <<'PY'
import pathlib
import sys
import zipfile

wheel = pathlib.Path(sys.argv[1]) / "zenml-0.0.0-py3-none-any.whl"
files = {
    "zenml_fixture.py": 'def main():\n    print("zenml, version 0.0.0")\n',
    "zenml-0.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: zenml\nVersion: 0.0.0\n",
    "zenml-0.0.0.dist-info/WHEEL": "Wheel-Version: 1.0\nGenerator: installer-regression\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
    "zenml-0.0.0.dist-info/entry_points.txt": "[console_scripts]\nzenml = zenml_fixture:main\n",
}
files["zenml-0.0.0.dist-info/RECORD"] = "".join(f"{name},,\n" for name in files)
with zipfile.ZipFile(wheel, "w") as archive:
    for name, content in files.items():
        archive.writestr(name, content)
PY

run_project() {
  local label="$1" environment="$2" workspace="$TMP/$1"
  mkdir -p "$workspace/member"
  cat > "$workspace/pyproject.toml" <<'TOML'
[project]
name = "installer-workspace"
version = "0.0.0"
requires-python = ">=3.10"
[tool.uv.workspace]
members = ["member"]
TOML
  cat > "$workspace/member/pyproject.toml" <<'TOML'
[project]
name = "installer-member"
version = "0.0.0"
requires-python = ">=3.10"
TOML
  # Pin at the workspace root, not the current member directory.
  if [ "${3:-pin}" = pin ]; then
    printf '%s\n' "$PYTHON" > "$workspace/.python-version"
  else
    uv venv --python "$PYTHON" "$workspace/.venv" >/dev/null 2>&1
  fi
  (
    cd "$workspace/member"
    if [ -n "$environment" ]; then export UV_PROJECT_ENVIRONMENT="$environment"; fi
    "$BASH" "$INSTALLER" --project --no-skills --no-modify-path --extras= --version=0.0.0 --verbose
  ) > "$TMP/$label.log" 2>&1 || { cat "$TMP/$label.log"; return 1; }
  local expected="$workspace/.venv"
  if [ -n "$environment" ]; then
    case "$environment" in /*) expected="$environment" ;; *) expected="$workspace/$environment" ;; esac
  fi
  [ -x "$expected/bin/zenml" ]
  grep -F "environment: $expected " "$TMP/$label.log" >/dev/null
  # A fallback --python would replace the inherited exact interpreter pin.
  if grep -F -- '--python >=3.10' "$TMP/$label.log"; then return 1; fi
  echo "PASS: $label"
}

case "${2:-all}" in
  all|workspace)
    run_project workspace ""
    run_project existing-env "" existing
    run_project relative-env custom-env
    run_project absolute-env "$TMP/absolute-venv"
    ;;
esac

case "${2:-all}" in
  all|bootstrap)
    # Exercise the production bootstrap function, stopping before its HOME-based
    # binary lookup. The stub cannot install uv or edit shell configuration.
    awk '/^install_uv\(\) \{/ { copy=1 } copy { print } copy && /^\}/ { exit }' "$INSTALLER" > "$TMP/bootstrap-function.sh"
    for flag in 0 1; do
      # The sourced production function calls these test doubles.
      # shellcheck disable=SC2329,SC2016
      (
        step() { :; }
        fetch_to_stdout() { printf 'printf "%%s" "${UV_NO_MODIFY_PATH:-unset}" > "$BOOTSTRAP_OBSERVED"\nexit 42\n'; }
        quiet() { "$@"; }
        die() { exit 42; }
        export BOOTSTRAP_OBSERVED="$TMP/bootstrap-$flag"
        unset UV_NO_MODIFY_PATH
        export ORIG_PATH="$PATH"
        export ZENML_INSTALL_NO_MODIFY_PATH="$flag"
        # shellcheck source=/dev/null
        source "$TMP/bootstrap-function.sh"
        install_uv
      ) && exit 1
      expected="unset"
      [ "$flag" = 1 ] && expected=1
      [ "$(cat "$TMP/bootstrap-$flag")" = "$expected" ]
      echo "PASS: bootstrap no-modify-path=$flag"
    done
    ;;
esac
