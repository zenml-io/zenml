#!/usr/bin/env bash

# update those variables accrodingly, if the new ZenML
# Dashboard version was released
RELEASE="v0.16.1"
LEGACY_RELEASE="v0.16.1"

APP_NAME="zenml-dashboard"
REPO_URL="https://github.com/zenml-io/zenml-dashboard"

: "${INSTALL_PATH:=./src/zenml/zen_server}"
: "${LEGACY_INSTALL_DIR:=dashboard_legacy}"
: "${INSTALL_DIR:=dashboard}"
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
    if grep -q -E "(^|\/)dashboard($|\/)" ".gitignore" || grep -q -E "(^|\/)src\/zenml\/zen_server\/dashboard($|\/)" ".gitignore"; then
      echo "Error: The '/dashboard' or 'src/zenml/zen_server/dashboard' directory is ignored by Git."
      echo "Please remove the corresponding entries from the .gitignore file to proceed with the installation."
      exit 1
    fi
  fi
}

# buildTags builds the TAG and LEGACY_TAG, if not already provided 
# as an environment variable
buildTags() {
  if [ -z "$LEGACY_TAG" ]; then
    local legacy_release_url="$REPO_URL/releases/$LEGACY_RELEASE"
    if type "curl" > /dev/null; then
      LEGACY_TAG=$(curl -Ls -o /dev/null -w '%{url_effective}' $legacy_release_url | grep -oE "[^/]+$" )
    elif type "wget" > /dev/null; then
      LEGACY_TAG=$(wget $legacy_release_url --server-response -O /dev/null 2>&1 | awk '/^\s*Location: /{DEST=$2} END{ print DEST}' | grep -oE "[^/]+$")
    fi
  fi

  if [ -z "$TAG" ]; then
    local release_url="$REPO_URL/releases/$RELEASE"
    if type "curl" > /dev/null; then
      TAG=$(curl -Ls -o /dev/null -w '%{url_effective}' $release_url | grep -oE "[^/]+$" )
    elif type "wget" > /dev/null; then
      TAG=$(wget $release_url --server-response -O /dev/null 2>&1 | awk '/^\s*Location: /{DEST=$2} END{ print DEST}' | grep -oE "[^/]+$")
    fi
  fi

}

# downloadFile downloads the latest release archive and checksum
downloadFile() {
  local local_tag=$1
  ZENML_DASHBOARD_ARCHIVE="zenml-dashboard.tar.gz"
  DOWNLOAD_URL="$REPO_URL/releases/download/$local_tag/$ZENML_DASHBOARD_ARCHIVE"
  TMP_ROOT="$(mktemp -dt zenml-dashboard-XXXXXX)"
  TMP_FILE="$TMP_ROOT/$ZENML_DASHBOARD_ARCHIVE"
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
  if [ "${VERIFY_CHECKSUM}" == "true" ]; then
    verifyChecksum
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
  printf "Verifying checksum... "
  local sum
  local expected_sum
  sum=$(openssl sha1 -sha256 "${TMP_FILE}" | awk '{print $2}')
  expected_sum=$(grep -i "${ZENML_DASHBOARD_ARCHIVE}" "${TMP_FILE}.sha256" | cut -f 1 -d " ")
  if [ "$sum" != "$expected_sum" ]; then
    echo "SHA sum of ${ZENML_DASHBOARD_ARCHIVE} does not match. Aborting."
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
buildTags
if [[ ! -z "$TAG" ]]; then
  downloadFile $TAG
  verifyFile
  installFile $INSTALL_DIR
fi
if [[ ! -z "$LEGACY_TAG" ]]; then
  downloadFile $LEGACY_TAG
  verifyFile
  installFile $LEGACY_INSTALL_DIR
fi
cleanup
