#!/usr/bin/env bash

set -eo pipefail

usage() {
  cat << EOF # remove the space between << and EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-f]

Script description here.

Available options:

-h, --help        When you use -h, this function is called and then script is exited
-y, --yes       Force the run including the removal of the old .zen folder and all old runs
--no-stack-setup  Don't setup a specific ZenML stack for this example.
-e, --executable  The python file that contains the code to run this example.
EOF
  exit
}

zenml_init() {

  if [ -n "$FORCE" ] && [ -n "$SETUP_STACK" ]; then
    if [ -d ".zen" ]; then
      msg "${ERROR}Existing .zen repo will be cleared before reinitializing."
      rm -rf ".zen"
    fi
  fi

  if [ -d ".zen" ]; then
    msg "${WARNING}Zenml already initialized, ${NOFORMAT}zenml init${WARNING} will not be executed."
  else
    zenml init
  fi
}

main() {
  NOFORMAT='\033[0m'
  ERROR='\033[0;31m'
  WARNING='\033[0;33m'

  REQUIREMENTS_TXT="requirements.txt"

  if [ -f "$REQUIREMENTS_TXT" ]; then
    python -m pip install -r requirements.txt
  fi

  zenml_init

  if [ -f "setup.sh" ]; then
    msg "This example requires some additional setup, setting up now..."
    source "./setup.sh"
    if [ -n "$FORCE" ]; then
      if [[ $(type -t pre_run_forced) == function ]]; then
        pre_run_forced
      fi
    else
      if [[ $(type -t pre_run) == function ]]; then
        pre_run
      fi
    fi

    if [ -n "$SETUP_STACK" ]; then
      if [[ $(type -t setup_stack) == function ]]; then
          setup_stack
      fi
    fi
  fi

  # Run the script
  python "$executable"

  if [ -f "setup.sh" ]; then
    if [[ $(type -t post_run) == function ]]; then
      post_run
    fi
  fi
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
  SETUP_STACK="true"

  while :; do
    case "${1-}" in
    -h | --help) usage ;;
    -y | --yes) FORCE="true";;
    --no-stack-setup) SETUP_STACK="";;
    -e | --executable)
      executable="${2-}"
      shift
      ;;
    -?*) die "Unknown option: $1" ;;
    *) break ;;
    esac
    shift
  done

  # check required params and arguments
  [[ -z "${executable-}" ]] && die "Missing required parameter: executable. Please supply a python file to run"

  return 0
}

parse_params "$@"
main "$@"


