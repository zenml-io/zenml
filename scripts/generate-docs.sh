#!/bin/sh -e
set -x

SRC="src/zenml/"
PUSH=""
LATEST=""
ONLY_CHECK=""

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
  -p | --push) PUSH="true";; # push to gh-pages branch
  -si | --skip_install) SKIP_INSTALL="true";; # skip pip install
  -l | --latest) LATEST="latest";; # set this docs version as latest
  -s | --source) # specify source directory
    SRC="${2-}"
    shift
    ;;
  -v | --version) # specify version
    VERSION="${2-}"
    shift
    ;;
  -c | --only-check) ONLY_CHECK="true";; # only check if docs are buildable with mockers
  -?*) die "Unknown option: $1" ;;
  *) break ;;
  esac
  shift
done

# check required params and arguments
[ -z "${VERSION-}" ] && die "Missing required parameter: VERSION. Please supply a doc version"

##################################################### Setup ############################################################
export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export DISABLE_DATABASE_MIGRATION=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
rm -rf docs/mkdocs/core_code_docs || true
rm -rf docs/mkdocs/integration_code_docs || true
rm docs/mkdocs/index.md || true

################################################ Install Requirements ##################################################
if [ -z "$SKIP_INSTALL" ]; then
  #pip3 install uv
  uv pip install --system -e ".[server,dev]"
  uv pip install --system "Jinja2==3.0.3"
fi

################################# Initialize DB and delete unnecessary alembic files ###################################

# env.py leads to errors in the build as run_migrations() gets executed
# the migration versions are not necessary parts of the api docs
rm -rf src/zenml/zen_stores/migrations/env.py
rm -rf src/zenml/zen_stores/migrations/versions
rm -rf src/zenml/zen_stores/migrations/script.py.mako


########################################## Generate Structure of API docs ##############################################
python3 docs/mkdocstrings_helper.py --path $SRC --output_path docs/mkdocs/


############################################## Build the API docs ####################################################
if [ -n "$ONLY_CHECK" ]; then
  python3 docs/sys_modules_mock.py
  mkdocs build --config-file docs/mkdocs.yml
else
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
fi
