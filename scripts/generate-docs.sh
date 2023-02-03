#!/bin/sh -e
set -x

SRC="src/zenml/"
PUSH=""
LATEST=""

msg() {
  echo >&2 -e "${1-}"
}

die() {
  msg=$1
  code=${2-1} # default exit status 1
  msg "$msg"
  exit "$code"
}

while :; do
  case "${1-}" in
  -p | --push) PUSH="true";;
  -l | --latest) LATEST="latest";;
  -s | --source)
    SRC="${2-}"
    shift
    ;;
  -v | --version)
    VERSION="${2-}"
    shift
    ;;
  -?*) die "Unknown option: $1" ;;
  *) break ;;
  esac
  shift
done

# check required params and arguments
[ -z "${VERSION-}" ] && die "Missing required parameter: VERSION. Please supply a doc version"

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export DISABLE_DATABASE_MIGRATION=1
rm -rf docs/mkdocs/core_code_docs || true
rm -rf docs/mkdocs/integration_code_docs || true
rm docs/mkdocs/index.md || true

python docs/mkdocstrings_helper.py --path $SRC --output_path docs/mkdocs/

if [ -n "$PUSH" ]; then
  if [ -n "$LATEST" ]; then
    mike deploy --push --update-aliases --config-file docs/mkdocs.yml $VERSION latest
  else
    mike deploy --push --update-aliases --config-file docs/mkdocs.yml $VERSION
  fi
else
  if [ -n "$LATEST" ]; then
    mike deploy --update-aliases --config-file docs/mkdocs.yml $VERSION latest
  else
    mike deploy --update-aliases --config-file docs/mkdocs.yml $VERSION
  fi
fi
