#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {

  zenml model-deployer register mlflow_quickstart --flavor=mlflow
  zenml experiment-tracker register mlflow_quickstart --flavor=mlflow
  zenml model-registry register mlflow_quickstart --flavor=mlflow
  zenml stack register quickstart \
      -a default \
      -o default \
      -d mlflow_quickstart \
      -r mlflow_quickstart \
      -e mlflow_quickstart || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}quickstart"

  zenml stack set quickstart
}

pre_run () {
  zenml integration install sklearn mlflow
}

pre_run_forced () {
  zenml integration install sklearn mlflow -y
}

post_run () {
  # cleanup the last local ZenML daemon started by the example
  pkill -n -f zenml.services.local.local_daemon_entrypoint
}
