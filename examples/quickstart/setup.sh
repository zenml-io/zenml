#!/usr/bin/env bash

set -Eeo pipefail

usage() {
  cat << EOF # remove the space between << and EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-f]

Script description here.

Available options:

-h, --help      When you use -h, this function is called and then script is exited
-f, --force     Force the run including the removal of the old .zen folder and all old runs
EOF
  exit
}

msg() {
  echo >&2 -e "${1-}"
}

die() {
  local msg=$1
  local code=${2-1} # default exit status 1
  msg "$msg"
  exit "$code"
}

parse_params() {
  # default values of variables
  FORCE=""

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -f | --force) FORCE="true";;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done
  return 0
}

parse_params "$@"

NOFORMAT='\033[0m'
ERROR='\033[0;31m'
WARNING='\033[0;33m'

git init

ZEN_DIR=".zen"
REQUIREMENTS_TXT="requirements.txt"
LOCAL_SETUP="setup.sh"

if [ -n "$FORCE" ]; then
  msg "${ERROR}Existing .zen repo will be cleared before reinitializing."
  rm -rf "$ZEN_DIR"
fi

if [ -d "$ZEN_DIR" ]; then
  msg "${WARNING}Zenml already initialized, ${NOFORMAT}zenml init${WARNING} will not be executed."
else
  zenml init
fi

if [ -f "$REQUIREMENTS_TXT" ]; then
  python3 -m pip install -r requirements.txt
fi

if [ -f "$LOCAL_SETUP" ]; then
  ./$LOCAL_SETUP
fi

# Run the script
python3 quickstart.py
