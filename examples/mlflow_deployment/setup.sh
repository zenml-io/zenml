#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml model-deployer register mlflow_deployer --type=mlflow || \
    msg "${WARNING}Reusing preexisting model deployer ${NOFORMAT}mlflow_deployer"
  zenml experiment-tracker register mlflow_tracker  --type=mlflow || \
    msg "${WARNING}Reusing preexisting experiment tracker ${NOFORMAT}mlflow_tracker"
  zenml stack register local_mlflow_stack \
      -m default \
      -a default \
      -o default \
      -d mlflow_deployer \
      -e mlflow_tracker || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_mlflow_stack"

  zenml stack set local_mlflow_stack
}

pre_run () {
  zenml integration install tensorflow
  zenml integration install mlflow
}

pre_run_forced () {
  zenml integration install tensorflow -y
  zenml integration install mlflow -y
}

post_run () {
  # cleanup the last local ZenML daemon started by the example
  pkill -n -f zenml.services.local.local_daemon_entrypoint
}
