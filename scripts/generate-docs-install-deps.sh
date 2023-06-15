#!/bin/sh -e
set -x

##################################################### Setup ############################################################
export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
export DISABLE_DATABASE_MIGRATION=1

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