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

##################################################### Setup ############################################################
export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export DISABLE_DATABASE_MIGRATION=1
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

zenml integration install -y feast
zenml integration install -y label_studio
zenml integration install -y bentoml
zenml integration install -y airflow
zenml integration install -y kserve
zenml integration install -y --ignore-integration feast --ignore-integration label_studio --ignore-integration kserve --ignore-integration airflow --ignore-integration bentoml
pip install -e ".[server,dev,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs]"
pip install jinja2==3.0.3 protobuf==3.20.0 numpy~=1.21.5
pip install typing-extensions --upgrade

################################# Initialize DB and delete unnecessary alembic files ###################################

# env.py leads to errors in the build as run_migrations() gets executed
# the migration versions are not necessary parts of the api docs
zenml status # to initialize the db
rm -rf src/zenml/zen_stores/migrations/env.py
rm -rf src/zenml/zen_stores/migrations/versions
rm -rf src/zenml/zen_stores/migrations/script.py.mako


########################################## Generate Structure of API docs ##############################################
python docs/mkdocstrings_helper.py --path $SRC --output_path docs/mkdocs/


################################################ Build the API docs ####################################################
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
