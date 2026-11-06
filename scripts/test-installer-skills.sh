#!/usr/bin/env bash
# Exercise the production skills functions without touching user configuration.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALLER="${1:-$ROOT/install-zenml.sh}"
TEST_TMP="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP"' EXIT
# The installer runs the functions inside main; extract only their definitions.
# shellcheck source=/dev/null
source <(sed -n '/^skill_destinations() {/,/^SKILL_NAMES=(); SKILL_DESTS=()/p' "$INSTALLER")
export ZENML_INSTALL_SKILLS_REPO=fixture/skills
mkdir -p "$TEST_TMP/archive/skills-main/skills/plugin/skills/example"
cat > "$TEST_TMP/archive/skills-main/skills/plugin/skills/example/SKILL.md" <<'MD'
---
name: zenml-example
---
Packaged skill
MD
printf 'Packaged note\n' > "$TEST_TMP/archive/skills-main/skills/plugin/skills/example/notes.txt"
tar -czf "$TEST_TMP/skills.tar.gz" -C "$TEST_TMP/archive" skills-main
fetch_to_stdout() { cat "$TEST_TMP/skills.tar.gz"; }
skill_destinations() { printf '%s\n' "$TEST_TMP/destination"; }
COPY_FAIL=0
COPY_RACE=0
COPY_CALLS=0
cp() {
  COPY_CALLS=$((COPY_CALLS + 1))
  if [ "$COPY_FAIL" = 1 ]; then
    mkdir -p "$3"
    printf 'Partial copy\n' > "$3/SKILL.md"
    return 1
  fi
  command cp "$@"
  if [ "$COPY_RACE" = 1 ]; then
    mkdir "$TEST_TMP/destination/zenml-example"
    printf 'Concurrent skill\n' > "$TEST_TMP/destination/zenml-example/SKILL.md"
  elif [ "$COPY_RACE" = 2 ]; then
    ln -s "$TEST_TMP/missing" "$TEST_TMP/destination/zenml-example"
  fi
}
reset_destination() {
  rm -rf "$TEST_TMP/destination"
  mkdir -p "$TEST_TMP/destination"
  COPY_CALLS=0
}
assert_no_staging() {
  [ "$(find "$TEST_TMP/destination" -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')" = "$1" ]
}

reset_destination
mkdir "$TEST_TMP/destination/zenml-example"
printf 'Custom skill\n' > "$TEST_TMP/destination/zenml-example/SKILL.md"
printf 'Local notes\n' > "$TEST_TMP/destination/zenml-example/local.txt"
install_skills
[ "$(cat "$TEST_TMP/destination/zenml-example/SKILL.md")" = 'Custom skill' ]
[ "$(cat "$TEST_TMP/destination/zenml-example/local.txt")" = 'Local notes' ]
[ "$COPY_CALLS" = 0 ]
echo 'PASS: preserves existing skill and local notes without copying'

COPY_FAIL=1
mkdir -p "$TEST_TMP/archive/skills-main/skills/plugin/skills/another"
printf '%s\n' '---' 'name: zenml-missing' '---' > "$TEST_TMP/archive/skills-main/skills/plugin/skills/another/SKILL.md"
tar -czf "$TEST_TMP/skills.tar.gz" -C "$TEST_TMP/archive" skills-main
if install_skills; then
  echo 'FAIL: failed additional skill copy reported success'; exit 1
fi
[ "$(cat "$TEST_TMP/destination/zenml-example/SKILL.md")" = 'Custom skill' ]
[ "$(cat "$TEST_TMP/destination/zenml-example/local.txt")" = 'Local notes' ]
[ "$COPY_CALLS" = 1 ]
[ ! -e "$TEST_TMP/destination/zenml-missing" ]
assert_no_staging 1
rm -rf "$TEST_TMP/archive/skills-main/skills/plugin/skills/another"
tar -czf "$TEST_TMP/skills.tar.gz" -C "$TEST_TMP/archive" skills-main
echo 'PASS: failed additional copy leaves an existing skill untouched'

reset_destination
if install_skills; then
  echo 'FAIL: partial copy reported success'; exit 1
fi
[ ! -e "$TEST_TMP/destination/zenml-example" ]
assert_no_staging 0
echo 'PASS: failed new copy leaves no target or staging files'

COPY_FAIL=0
install_skills
[ "$(cat "$TEST_TMP/destination/zenml-example/SKILL.md")" = "$(cat "$TEST_TMP/archive/skills-main/skills/plugin/skills/example/SKILL.md")" ]
[ "$(cat "$TEST_TMP/destination/zenml-example/notes.txt")" = 'Packaged note' ]
assert_no_staging 1
echo 'PASS: installs a complete new skill'

for target in "$TEST_TMP/missing" "$TEST_TMP/archive/skills-main/skills/plugin/skills/example"; do
  reset_destination
  ln -s "$target" "$TEST_TMP/destination/zenml-example"
  install_skills
  [ -L "$TEST_TMP/destination/zenml-example" ]
  [ "$(readlink "$TEST_TMP/destination/zenml-example")" = "$target" ]
  [ "$COPY_CALLS" = 0 ]
  assert_no_staging 1
done
echo 'PASS: preserves symlinks, including dangling links'

for COPY_RACE in 1 2; do
  reset_destination
  install_skills
  if [ "$COPY_RACE" = 1 ]; then
    [ "$(cat "$TEST_TMP/destination/zenml-example/SKILL.md")" = 'Concurrent skill' ]
    [ ! -e "$TEST_TMP/destination/zenml-example/zenml-example" ]
  else
    [ -L "$TEST_TMP/destination/zenml-example" ]
    [ "$(readlink "$TEST_TMP/destination/zenml-example")" = "$TEST_TMP/missing" ]
  fi
  [ "$SKILLS_ADDED" = 0 ]
  [ "$SKILLS_PRESERVED" = 1 ]
  assert_no_staging 1
done
echo 'PASS: preserves paths created during copying without nesting a skill'
