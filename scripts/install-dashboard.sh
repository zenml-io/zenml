#!/usr/bin/env bash
# Bundle the highest stable zenml-ui release from the frontend monorepo.
# TAG (or ZENML_UI_TAG) selects an exact release independently of ZenML's version.
# ZENML_UI_RELEASE_TOKEN needs Contents: read access to the private repository.
# ZENML_UI_ALLOW_PRERELEASE=true permits an explicitly selected prerelease.
# INSTALL_PATH, INSTALL_DIR, VERIFY_CHECKSUM, and PYTHON_BIN can be overridden.

# Authenticated requests must never be printed by shell tracing.
set +x
set -euo pipefail

REPO="${ZENML_UI_RELEASE_REPO:-zenml-io/zenml-frontend-monorepo}"
API_URL="${GITHUB_API_URL:-https://api.github.com}"
ARCHIVE_NAME="zenml-dashboard.tar.gz"
INSTALL_PATH="${INSTALL_PATH:-./src/zenml/zen_server}"
INSTALL_DIR="${INSTALL_DIR:-dashboard}"
VERIFY_CHECKSUM="${VERIFY_CHECKSUM:-true}"
ALLOW_PRERELEASE="${ZENML_UI_ALLOW_PRERELEASE:-false}"
TAG="${TAG:-${ZENML_UI_TAG:-}}"
TMP_DIR=""

cleanup() {
  if [ -n "$TMP_DIR" ]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
Usage: bash scripts/install-dashboard.sh

Downloads the highest stable zenml-ui-v<semver> release by default.
Set ZENML_UI_RELEASE_TOKEN to a token with Contents: read access to
zenml-io/zenml-frontend-monorepo. Public PyPI/Docker installs already bundle
these files and do not need a token.

Optional environment variables:
  TAG / ZENML_UI_TAG            Exact zenml-ui-v<semver> release tag
  ZENML_UI_ALLOW_PRERELEASE     true to permit an explicit prerelease
  INSTALL_PATH                 Destination parent (./src/zenml/zen_server)
  INSTALL_DIR                  Destination directory name (dashboard)
  VERIFY_CHECKSUM               false to disable SHA256 verification
  PYTHON_BIN                   Python executable (python3 or python)
HELP
  exit 0
elif [ "$#" -ne 0 ]; then
  echo "Error: unexpected arguments. Use --help for usage." >&2
  exit 1
fi

if ! command -v curl >/dev/null; then
  echo "Error: curl is required to download the dashboard." >&2
  exit 1
fi
if [ -z "${PYTHON_BIN:-}" ]; then
  if command -v python3 >/dev/null; then
    PYTHON_BIN=python3
  else
    PYTHON_BIN=python
  fi
fi
if ! command -v "$PYTHON_BIN" >/dev/null; then
  echo "Error: Python 3 is required to select and verify dashboard releases." >&2
  exit 1
fi
if [ -z "${ZENML_UI_RELEASE_TOKEN:-}" ]; then
  echo "Error: set ZENML_UI_RELEASE_TOKEN to a token with Contents: read access to $REPO." >&2
  exit 1
fi

# Downloaded files must remain visible to the Python package builder.
if [ -f .gitignore ] && grep -q -E '(^|/)dashboard($|/)|(^|/)src/zenml/zen_server/dashboard($|/)' .gitignore; then
  echo "Error: the dashboard directory must not be ignored by .gitignore." >&2
  exit 1
fi
if [[ "$INSTALL_DIR" == */* || "$INSTALL_DIR" == "." || "$INSTALL_DIR" == ".." ]]; then
  echo "Error: INSTALL_DIR must be a directory name, not a path." >&2
  exit 1
fi

request() {
  local url="$1" accept="$2" destination="$3"
  if ! curl -fSsL \
      -H "Accept: $accept" \
      -H 'X-GitHub-Api-Version: 2022-11-28' \
      -H "Authorization: Bearer $ZENML_UI_RELEASE_TOKEN" \
      "$url" -o "$destination"; then
    echo "Error: could not download $url. Check the release and ZENML_UI_RELEASE_TOKEN repository access." >&2
    return 1
  fi
}

resolve_tag() {
  if [ -n "$TAG" ]; then
    return
  fi

  local page=1 count page_file
  local -a page_files=()
  while true; do
    page_file="$TMP_DIR/releases-$page.json"
    request "$API_URL/repos/$REPO/releases?per_page=100&page=$page" application/vnd.github+json "$page_file"
    page_files+=("$page_file")
    count=$("$PYTHON_BIN" - "$page_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    releases = json.load(handle)
if not isinstance(releases, list):
    sys.exit("Error: GitHub releases response was not an array.")
print(len(releases))
PY
)
    if [ "$count" -lt 100 ]; then
      break
    fi
    page=$((page + 1))
  done

  TAG=$("$PYTHON_BIN" - "${page_files[@]}" <<'PY'
import json
import re
import sys

pattern = re.compile(r"^zenml-ui-v(\d+)\.(\d+)\.(\d+)(?:\+[0-9A-Za-z][0-9A-Za-z.-]*)?$")
candidates = []
for page in sys.argv[1:]:
    with open(page, encoding="utf-8") as handle:
        releases = json.load(handle)
    for release in releases:
        tag = str(release.get("tag_name", ""))
        match = pattern.fullmatch(tag)
        if match and not release.get("draft") and not release.get("prerelease"):
            candidates.append((tuple(map(int, match.groups())), tag))
if not candidates:
    sys.exit("Error: no stable zenml-ui-v<semver> releases found.")
print(max(candidates)[1])
PY
)
}

load_asset_urls() {
  "$PYTHON_BIN" - "$TMP_DIR/release.json" "$TAG" "$ALLOW_PRERELEASE" "$ARCHIVE_NAME" <<'PY'
import json
import re
import sys

path, tag, allow_prerelease, archive_name = sys.argv[1:]
with open(path, encoding="utf-8") as handle:
    release = json.load(handle)
if release.get("draft"):
    sys.exit(f"Error: release {tag} is a draft and cannot be bundled.")
if release.get("prerelease") or re.match(r"^zenml-ui-v\d+\.\d+\.\d+-", tag):
    if allow_prerelease != "true":
        sys.exit(f"Error: release {tag} is a prerelease. Set ZENML_UI_ALLOW_PRERELEASE=true to opt in.")
assets = {asset["name"]: asset for asset in release.get("assets", [])}
for name in (archive_name, f"{archive_name}.sha256"):
    asset = assets.get(name)
    if not asset or not asset.get("url"):
        sys.exit(f"Error: release {tag} is missing the required asset {name}.")
    # Private assets are downloaded through the API, not browser URLs.
    print(asset["url"])
PY
}

install_archive() {
  "$PYTHON_BIN" - "$TMP_DIR" "$ARCHIVE_NAME" "$VERIFY_CHECKSUM" <<'PY'
import hashlib
import sys
import tarfile
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1])
archive = root / sys.argv[2]
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
if sys.argv[3] != "false":
    expected = (root / f"{sys.argv[2]}.sha256").read_text().split()[0]
    if checksum != expected:
        sys.exit("Error: dashboard SHA256 checksum mismatch.")
print(f"Dashboard SHA256: {checksum}")
# Validate members before extraction so an invalid archive cannot write outside
# the staging directory or replace a previously installed dashboard.
with tarfile.open(archive, "r:gz") as bundle:
    for member in bundle.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            sys.exit(f"Error: unsafe dashboard archive entry: {member.name}")
PY
  mkdir "$TMP_DIR/extracted"
  tar xzf "$TMP_DIR/$ARCHIVE_NAME" -C "$TMP_DIR/extracted"
  if [ ! -f "$TMP_DIR/extracted/index.html" ] || [ ! -d "$TMP_DIR/extracted/assets" ]; then
    echo "Error: dashboard archive must contain index.html and assets/." >&2
    return 1
  fi
  mkdir -p "$INSTALL_PATH"
  rm -rf "${INSTALL_PATH:?}/${INSTALL_DIR:?}"
  mv "$TMP_DIR/extracted" "$INSTALL_PATH/$INSTALL_DIR"
}

TMP_DIR=$(mktemp -d -t zenml-dashboard-XXXXXX)
resolve_tag
TAG_PATTERN='^zenml-ui-v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z][0-9A-Za-z.-]*)?(\+[0-9A-Za-z][0-9A-Za-z.-]*)?$'
if [[ ! "$TAG" =~ $TAG_PATTERN ]]; then
  echo "Error: TAG must use zenml-ui-v<semver>, received: $TAG" >&2
  exit 1
fi
echo "Selected dashboard release: $REPO@$TAG"
request "$API_URL/repos/$REPO/releases/tags/$TAG" application/vnd.github+json "$TMP_DIR/release.json"
load_asset_urls > "$TMP_DIR/asset-urls"
archive_url=$(sed -n '1p' "$TMP_DIR/asset-urls")
checksum_url=$(sed -n '2p' "$TMP_DIR/asset-urls")
request "$archive_url" application/octet-stream "$TMP_DIR/$ARCHIVE_NAME"
request "$checksum_url" application/octet-stream "$TMP_DIR/$ARCHIVE_NAME.sha256"
install_archive
echo "Dashboard $TAG installed into $INSTALL_PATH/$INSTALL_DIR"
