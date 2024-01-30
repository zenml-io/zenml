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
  -p | --push) PUSH="true";;
  -si | --skip_install) SKIP_INSTALL="true";;
  -l | --latest) LATEST="latest";;
  -s | --source)
    SRC="${2-}"
    shift
    ;;
  -v | --version)
    VERSION="${2-}"
    shift
    ;;
  -c | --only-check) ONLY_CHECK="true";;
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
# IMPORTANT: there's a strategy to installing integrations here in a way
# that avoids conflicts while at the same time making it possible for all
# ZenML Python modules to be imported, especially the integration modules:
# 1. install zenml with all extras
# 2. install more restrictive integrations first: feast and
# label_studio are currently the ones known to be very restrictive in
# terms of what versions of dependencies they require
# 3. Install bentoml because of its attrs version
# 4. Install airflow because of its attrs version>=22.1.0
# 5. install the rest of the integrations (where aws depends on attrs==20.3.0)
# 6. as the last step, install zenml again (step 1. repeated)
# 7. Reinstall jinja in the correct version as the contexthandler is
# deprecated in 3.1.0 but mkdocstring depends on this method

if [ -z "$SKIP_INSTALL" ]; then
  pip install -e ".[server,dev]"
fi

################################# Initialize DB and delete unnecessary alembic files ###################################

# env.py leads to errors in the build as run_migrations() gets executed
# the migration versions are not necessary parts of the api docs
zenml status # to initialize the db
rm -rf src/zenml/zen_stores/migrations/env.py
rm -rf src/zenml/zen_stores/migrations/versions
rm -rf src/zenml/zen_stores/migrations/script.py.mako


########################################## Generate Structure of API docs ##############################################
python docs/mkdocstrings_helper.py --path $SRC --output_path docs/mkdocs/


############################################## Build the API docs ####################################################
if [ -n "$ONLY_CHECK" ]; then
  python3 docs/sys_modules_mock.py
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
