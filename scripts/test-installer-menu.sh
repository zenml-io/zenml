#!/usr/bin/env bash
# Exercise menu resolution and environment handoff with real uv and local wheels.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MENU="${1:-$ROOT/install.sh}"
MENU="$(cd "$(dirname "$MENU")" && pwd)/$(basename "$MENU")"
PYTHON="$(uv python find --no-python-downloads ">=3.11,<3.14")"
command -v uv >/dev/null
TEST_TMP="$(mktemp -d)"
TEST_TMP="$(cd "$TEST_TMP" && pwd -P)"
trap 'rm -rf "$TEST_TMP"' EXIT
UV_PYTHON_INSTALL_DIR="$(uv python dir)"
export UV_CACHE_DIR="$TEST_TMP/cache" UV_PYTHON_INSTALL_DIR
export UV_TOOL_DIR="$TEST_TMP/tools" UV_TOOL_BIN_DIR="$TEST_TMP/bin"
export XDG_CONFIG_HOME="$TEST_TMP/config" XDG_DATA_HOME="$TEST_TMP/data"
export XDG_CACHE_HOME="$TEST_TMP/xdg-cache" ZENML_CONFIG_PATH="$TEST_TMP/zenml"
export UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never UV_NO_CONFIG=1 UV_NO_CACHE=1
export UV_NO_INDEX=1 UV_FIND_LINKS="$TEST_TMP/wheels"
export ZENML_INSTALL_VERSION=0.98.1 KITARU_VERSION=0.98.1
export ZENML_INSTALL_PYTHON="$PYTHON" KITARU_PYTHON="$PYTHON"
export ZENML_INSTALL_ZENML_URL="$ROOT/install-zenml.sh"
export ZENML_INSTALL_KITARU_URL="$TEST_TMP/install-kitaru.sh"
export MENU_TEST_LOG="$TEST_TMP/kitaru.log"
unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_PYTHON UV_CONSTRAINT UV_PROJECT UV_WORKING_DIR UV_FROZEN UV_NO_SYNC
unset ZENML_INSTALL_SCOPE KITARU_SCOPE
mkdir -p "$TEST_TMP/wheels"
# These wheels test the menu, not the applications or Kitaru's agent setup.
cat > "$TEST_TMP/make-wheels.py" <<'PY'
import pathlib
import sys
import zipfile

version = sys.argv[2]
for name, minimum in (("zenml", "3.10"), ("kitaru", "3.11")):
    metadata = f"{name}-{version}.dist-info"
    files = {
        f"{name}_fixture.py": f'def main():\n    from importlib.metadata import version\n    print("{name}, version " + version("{name}"))\n',
        f"{metadata}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
            f"Requires-Python: >={minimum}\n"
            "Provides-Extra: local\nProvides-Extra: cli\n"
            "Provides-Extra: mcp\nProvides-Extra: worker\n"
        ),
        f"{metadata}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{metadata}/entry_points.txt": f"[console_scripts]\n{name} = {name}_fixture:main\n",
    }
    files[f"{metadata}/RECORD"] = "".join(f"{path},,\n" for path in files)
    wheel = pathlib.Path(sys.argv[1]) / f"{name}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
PY
"$PYTHON" "$TEST_TMP/make-wheels.py" "$TEST_TMP/wheels" 0.98.1

# Mimic Kitaru's dependency add and member-local executable lookup. The menu
# must supply an absolute environment path for that lookup in a workspace.
cat > "$ZENML_INSTALL_KITARU_URL" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
scope="${KITARU_SCOPE:-auto}"
for arg in "$@"; do
  case "$arg" in --project|--global) scope="${arg#--}" ;; esac
done
if [ "$scope" = auto ]; then
  scope=global
  if [ -f pyproject.toml ] || [ -f uv.lock ]; then scope=project; fi
fi
printf '%s\n' "${UV_PROJECT_ENVIRONMENT:-unset}" >> "$MENU_TEST_LOG"
if [ "$scope" = project ]; then
  if [ -n "${MENU_TEST_VERSION_LOG:-}" ]; then
    "${UV_PROJECT_ENVIRONMENT:-$PWD/.venv}/bin/kitaru" --version > "$MENU_TEST_VERSION_LOG"
  fi
  spec="kitaru[cli,mcp,worker]"
  [ -z "${KITARU_VERSION:-}" ] || spec="$spec==$KITARU_VERSION"
  uv add --quiet --upgrade-package kitaru "$spec"
  "${UV_PROJECT_ENVIRONMENT:-$PWD/.venv}/bin/kitaru" --version
else
  uv tool install --quiet --python "$KITARU_PYTHON" "kitaru[cli,mcp,worker]==$KITARU_VERSION"
fi
SH

make_project() {
  mkdir -p "$1"
  cat > "$1/pyproject.toml" <<TOML
[project]
name = "menu-${1##*/}"
version = "0.0.0"
requires-python = "$2"
dependencies = []
TOML
  printf '%s\n' "$PYTHON" > "$1/.python-version"
}

run_menu() {
  local directory="$1"
  shift
  rm -f "$MENU_TEST_LOG"
  (cd "$directory" && "$BASH" "$MENU" --products=zenml,kitaru --no-skills --no-modify-path "$@")
}

make_project "$TEST_TMP/incompatible" '>=3.10'
cp "$TEST_TMP/incompatible/pyproject.toml" "$TEST_TMP/before.toml"
if run_menu "$TEST_TMP/incompatible" --project > "$TEST_TMP/incompatible.log" 2>&1; then
  echo 'FAIL: incompatible project was accepted'; exit 1
fi
grep -Ei 'shared.*install.*fail|combined.*fail' "$TEST_TMP/incompatible.log" >/dev/null
cmp "$TEST_TMP/before.toml" "$TEST_TMP/incompatible/pyproject.toml"
[ ! -f "$TEST_TMP/incompatible/uv.lock" ]
[ ! -f "$TEST_TMP/incompatible/.venv/bin/zenml" ]
[ ! -f "$MENU_TEST_LOG" ]
echo 'PASS: incompatible project fails before either package is installed'

make_project "$TEST_TMP/compatible" '>=3.11'
run_menu "$TEST_TMP/compatible" --project > "$TEST_TMP/compatible.log" 2>&1 \
  || { cat "$TEST_TMP/compatible.log"; exit 1; }
grep -F 'zenml[local]' "$TEST_TMP/compatible/pyproject.toml" >/dev/null
grep -F 'kitaru[cli,mcp,worker]' "$TEST_TMP/compatible/pyproject.toml" >/dev/null
[ "$(cat "$MENU_TEST_LOG")" = "$TEST_TMP/compatible/.venv" ]
echo 'PASS: compatible project installs both packages'

make_project "$TEST_TMP/workspace" '>=3.11'
cat >> "$TEST_TMP/workspace/pyproject.toml" <<'TOML'
[tool.uv.workspace]
members = ["member"]
TOML
make_project "$TEST_TMP/workspace/member" '>=3.11'
rm "$TEST_TMP/workspace/member/.python-version"
run_menu "$TEST_TMP/workspace/member" > "$TEST_TMP/workspace.log" 2>&1 \
  || { cat "$TEST_TMP/workspace.log"; exit 1; }
[ "$(cat "$MENU_TEST_LOG")" = "$TEST_TMP/workspace/.venv" ]
echo 'PASS: both installers use the workspace environment'

run_menu "$TEST_TMP/incompatible" --project --global > "$TEST_TMP/global.log" 2>&1 \
  || { cat "$TEST_TMP/global.log"; exit 1; }
cmp "$TEST_TMP/before.toml" "$TEST_TMP/incompatible/pyproject.toml"
"$UV_TOOL_DIR/zenml/bin/python" -c 'from importlib.util import find_spec; assert find_spec("kitaru_fixture") is None'
[ -x "$UV_TOOL_BIN_DIR/zenml" ] && [ -x "$UV_TOOL_BIN_DIR/kitaru" ]
echo 'PASS: last scope flag wins and global tools remain isolated'

ZENML_INSTALL_SCOPE=project KITARU_SCOPE=global run_menu "$TEST_TMP/incompatible" > "$TEST_TMP/mixed.log" 2>&1 \
  || { cat "$TEST_TMP/mixed.log"; exit 1; }
grep -F 'zenml[local]' "$TEST_TMP/incompatible/pyproject.toml" >/dev/null
if grep -F 'kitaru[' "$TEST_TMP/incompatible/pyproject.toml"; then exit 1; fi
echo 'PASS: per-product scope overrides remain independent'

# Read the actual Kitaru version before the second installer can upgrade it.
make_project "$TEST_TMP/upgrade" '>=3.11'
run_menu "$TEST_TMP/upgrade" --project > "$TEST_TMP/upgrade-initial.log" 2>&1 \
  || { cat "$TEST_TMP/upgrade-initial.log"; exit 1; }
"$PYTHON" "$TEST_TMP/make-wheels.py" "$TEST_TMP/wheels" 0.98.2
# The first install intentionally pinned both packages; relax that user choice
# for this separate ordinary-upgrade case.
sed 's/==0.98.1/>=0.98.1/g' "$TEST_TMP/upgrade/pyproject.toml" > "$TEST_TMP/upgrade/new.toml"
mv "$TEST_TMP/upgrade/new.toml" "$TEST_TMP/upgrade/pyproject.toml"
unset ZENML_INSTALL_VERSION KITARU_VERSION
export MENU_TEST_VERSION_LOG="$TEST_TMP/version-before-kitaru.log"
run_menu "$TEST_TMP/upgrade" --project > "$TEST_TMP/upgrade.log" 2>&1 \
  || { cat "$TEST_TMP/upgrade.log"; exit 1; }
grep -F '0.98.2' "$MENU_TEST_VERSION_LOG" >/dev/null
[ "$("$TEST_TMP/upgrade/.venv/bin/zenml" --version)" = 'zenml, version 0.98.2' ]
echo 'PASS: first joint resolution upgrades both packages before Kitaru setup'

# Extract the real question and supply EOF without requiring a controlling TTY.
# shellcheck disable=SC2016  # Expand MENU_TEST_INPUT when the extracted function runs.
awk '/^ask_products\(\) \{/ { copy=1 } copy { print } copy && /^\}/ { exit }' "$MENU" \
  | sed 's#>/dev/tty#>/dev/null#g; s#</dev/tty#< "$MENU_TEST_INPUT"#g' > "$TEST_TMP/question.sh"
: > "$TEST_TMP/empty"
(
  # shellcheck source=/dev/null
  source "$TEST_TMP/question.sh"
  export C_PURPLE="" C_RESET="" C_BOLD="" C_DIM=""
  export MENU_TEST_INPUT="$TEST_TMP/empty"
  # shellcheck disable=SC2329  # Called by the extracted question function.
  die() { printf '%s\n' "$*" >&2; exit 1; }
  ask_products
) > "$TEST_TMP/eof.log" 2>&1 && { echo 'FAIL: EOF selected a product'; exit 1; }
grep -Ei 'cancel|no choice|end of input' "$TEST_TMP/eof.log" >/dev/null
echo 'PASS: question EOF cancels instead of installing the default'

for value in missing next-option; do
  args=(--products)
  [ "$value" != next-option ] || args+=(--global)
  if "$BASH" "$MENU" "${args[@]}" > "$TEST_TMP/flag.log" 2>&1; then
    echo 'FAIL: missing --products value accepted'; exit 1
  fi
  grep -F -- '--products' "$TEST_TMP/flag.log" >/dev/null
  grep -Ei 'requires|value|missing|expected' "$TEST_TMP/flag.log" >/dev/null
done
echo 'PASS: missing products values explain the invalid flag'
