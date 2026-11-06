#!/usr/bin/env bash
# Exercise menu resolution and environment handoff with real uv and local wheels.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MENU="${1:-$ROOT/install.sh}"
MENU="$(cd "$(dirname "$MENU")" && pwd)/$(basename "$MENU")"
PYTHON="$(command -v python3)"
command -v uv >/dev/null
TEST_TMP="$(mktemp -d)"
TEST_TMP="$(cd "$TEST_TMP" && pwd -P)"
trap 'rm -rf "$TEST_TMP"' EXIT
export UV_CACHE_DIR="$TEST_TMP/cache" UV_PYTHON_INSTALL_DIR="$TEST_TMP/python"
export UV_TOOL_DIR="$TEST_TMP/tools" UV_TOOL_BIN_DIR="$TEST_TMP/bin"
export XDG_CONFIG_HOME="$TEST_TMP/config" XDG_DATA_HOME="$TEST_TMP/data"
export XDG_CACHE_HOME="$TEST_TMP/xdg-cache" ZENML_CONFIG_PATH="$TEST_TMP/zenml"
export UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never UV_NO_CONFIG=1
export UV_NO_INDEX=1 UV_FIND_LINKS="$TEST_TMP/wheels"
export ZENML_INSTALL_VERSION=0.0.0 KITARU_VERSION=0.0.0
export ZENML_INSTALL_PYTHON="$PYTHON" KITARU_PYTHON="$PYTHON"
export ZENML_INSTALL_ZENML_URL="$ROOT/install-zenml.sh"
export ZENML_INSTALL_KITARU_URL="$TEST_TMP/install-kitaru.sh"
export MENU_TEST_LOG="$TEST_TMP/kitaru.log"
unset VIRTUAL_ENV UV_PROJECT_ENVIRONMENT UV_PYTHON UV_CONSTRAINT
unset ZENML_INSTALL_SCOPE KITARU_SCOPE
mkdir -p "$TEST_TMP/wheels"
# These wheels test the menu, not the applications or Kitaru's agent setup.
"$PYTHON" - "$TEST_TMP/wheels" <<'PY'
import pathlib
import sys
import zipfile

for name, minimum in (("zenml", "3.10"), ("kitaru", "3.11")):
    metadata = f"{name}-0.0.0.dist-info"
    files = {
        f"{name}_fixture.py": f'def main():\n    print("{name}, version 0.0.0")\n',
        f"{metadata}/METADATA": (
            f"Metadata-Version: 2.1\nName: {name}\nVersion: 0.0.0\n"
            f"Requires-Python: >={minimum}\n"
            "Provides-Extra: local\nProvides-Extra: cli\n"
            "Provides-Extra: mcp\nProvides-Extra: worker\n"
        ),
        f"{metadata}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{metadata}/entry_points.txt": f"[console_scripts]\n{name} = {name}_fixture:main\n",
    }
    files[f"{metadata}/RECORD"] = "".join(f"{path},,\n" for path in files)
    wheel = pathlib.Path(sys.argv[1]) / f"{name}-0.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
PY

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
  uv add --quiet "kitaru[cli,mcp,worker]==$KITARU_VERSION"
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
  (cd "$directory" && bash "$MENU" --products=zenml,kitaru --no-skills --no-modify-path "$@")
}

make_project "$TEST_TMP/incompatible" '>=3.10'
cp "$TEST_TMP/incompatible/pyproject.toml" "$TEST_TMP/before.toml"
if run_menu "$TEST_TMP/incompatible" --project > "$TEST_TMP/incompatible.log" 2>&1; then
  echo 'FAIL: incompatible project was accepted'; exit 1
fi
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
