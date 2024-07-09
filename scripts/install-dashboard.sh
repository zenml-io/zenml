#!/usr/bin/env bash

APP_NAME="zenml-dashboard"
REPO_URL="https://github.com/zenml-io/zenml-dashboard"

: "${INSTALL_PATH:=./src/zenml/zen_server}"
: "${INSTALL_DIR:=dashboard}"
: "${LEGACY_INSTALL_DIR:=dashboard_legacy}"
: "${VERIFY_CHECKSUM:=true}"
# : "${DESIRED_VERSION:=latest}"

HAS_OPENSSL="$(type "openssl" &> /dev/null && echo true || echo false)"


# verifySupported checks that all requirements are installed
verifySupported() {
  if ! type "curl" > /dev/null && ! type "wget" > /dev/null; then
    echo "Either curl or wget is required"
    exit 1
  fi

  if [ "${VERIFY_CHECKSUM}" == "true" ] && [ "${HAS_OPENSSL}" != "true" ]; then
    echo "In order to verify checksum, openssl must first be installed."
    echo "Please install openssl or set VERIFY_CHECKSUM=false in your environment."
    exit 1
  fi
}

# checkGitIgnore checks if the dashboard directories are ignored by Git
checkGitIgnore() {
  if [ -f ".gitignore" ]; then
    if grep -q -E "(^|\/)dashboard($|\/)" ".gitignore" || grep -q -E "(^|\/)src\/zenml\/zen_server\/dashboard($|\/)" ".gitignore" || grep -q -E "(^|\/)dashboard-legacy($|\/)" ".gitignore" || grep -q -E "(^|\/)src\/zenml\/zen_server\/dashboard-legacy($|\/)" ".gitignore"; then
      echo "Error: The '/dashboard', '/dashboard-legacy', 'src/zenml/zen_server/dashboard-legacy' or 'src/zenml/zen_server/dashboard' directory is ignored by Git."
      echo "Please remove the corresponding entries from the .gitignore file to proceed with the installation."
      exit 1
    fi
  fi
}

# checkTagProvided checks whether TAG has provided as an environment variable
# so we can skip checkLatestVersion
checkTagProvided() {
  if [ -n "$TAG" ]; then
    return 0
  fi
  return 1
}

# checkLatestVersion grabs the latest version string from the releases
checkLatestVersion() {
  local latest_release_url="$REPO_URL/releases/latest"
  if type "curl" > /dev/null; then
    TAG=$(curl -Ls -o /dev/null -w '%{url_effective}' $latest_release_url | grep -oE "[^/]+$" )
  elif type "wget" > /dev/null; then
    TAG=$(wget $latest_release_url --server-response -O /dev/null 2>&1 | awk '/^\s*Location: /{DEST=$2} END{ print DEST}' | grep -oE "[^/]+$")
  fi
}

# downloadFile downloads the latest release archive and checksum
downloadFile() {
  local archive_name=$1
  DOWNLOAD_URL="$REPO_URL/releases/download/$TAG/$archive_name"
  TMP_ROOT="$(mktemp -dt zenml-dashboard-XXXXXX)"
  TMP_FILE="$TMP_ROOT/$archive_name"
  if type "curl" > /dev/null; then
    curl -SsL "$DOWNLOAD_URL" -o "$TMP_FILE"
    curl -SsL "$DOWNLOAD_URL.sha256" -o "$TMP_FILE.sha256"
  elif type "wget" > /dev/null; then
    wget -q -O "$TMP_FILE" "$DOWNLOAD_URL"
    wget -q -O "$TMP_FILE.sha256" "$DOWNLOAD_URL.sha256"
  fi
}

# verifyFile verifies the SHA256 checksum of the binary package
# (depending on settings in environment).
verifyFile() {
  local archive_name=$1
  if [ "${VERIFY_CHECKSUM}" == "true" ]; then
    verifyChecksum "$archive_name"
  fi
}

# installFile unpacks and installs the binary.
installFile() {
  local local_install_dir=$1
  local current_dir=$(pwd)
  echo "Preparing to install $APP_NAME into ${INSTALL_PATH}/${local_install_dir}"
  cd "$INSTALL_PATH"
  rm -rf "$local_install_dir"
  mkdir -p "$local_install_dir"
  tar xzf "$TMP_FILE" -C "$local_install_dir"
  echo "$APP_NAME installed into $INSTALL_PATH/$local_install_dir"
  cd "$current_dir"
}

# verifyChecksum verifies the SHA256 checksum of the binary package.
verifyChecksum() {
  local archive_name=$1
  printf "Verifying checksum... "
  local sum
  local expected_sum
  sum=$(openssl sha1 -sha256 "${TMP_FILE}" | awk '{print $2}')
  expected_sum=$(grep -i "${archive_name}" "${TMP_FILE}.sha256" | cut -f 1 -d " ")
  if [ "$sum" != "$expected_sum" ]; then
    echo "SHA sum of ${archive_name} does not match. Aborting."
    exit 1
  fi
  echo "Done."
}

# fail_trap is executed if an error occurs.
fail_trap() {
  result=$?
  if [ "$result" != "0" ]; then
    if [[ -n "$INPUT_ARGUMENTS" ]]; then
      echo "Failed to install $APP_NAME with the arguments provided: $INPUT_ARGUMENTS"
      help
    else
      echo "Failed to install $APP_NAME"
    fi
    echo -e "\tFor support, go to $REPO_URL"
  fi
  cleanup
  exit $result
}

# help provides possible cli installation arguments
help () {
  echo "Accepted cli arguments are:"
  echo -e "\t[--help|-h ] ->> prints this help"
}

# cleanup temporary files
cleanup() {
  if [[ -d "${TMP_ROOT:-}" ]]; then
    rm -rf "$TMP_ROOT"
  fi
}

# Execution

#Stop execution on any error
trap "fail_trap" EXIT
set -e
set -x

# Parsing input arguments (if any)
export INPUT_ARGUMENTS="$*"
set -u
while [[ $# -gt 0 ]]; do
  case $1 in
    '--help'|-h)
       help
       exit 0
       ;;
    *) exit 1
       ;;
  esac
  shift
done
set +u

verifySupported
checkGitIgnore
checkTagProvided || checkLatestVersion
if [[ -n "$TAG" ]]; then
  downloadFile "zenml-dashboard.tar.gz"
  verifyFile "zenml-dashboard.tar.gz"
  installFile "$INSTALL_DIR"

  downloadFile "zenml-dashboard-legacy.tar.gz"
  verifyFile "zenml-dashboard-legacy.tar.gz"
  installFile "$LEGACY_INSTALL_DIR"
fi
cleanup
