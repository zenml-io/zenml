#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml model-deployer register mlflow_deployer --flavor=mlflow || \
    msg "${WARNING}Reusing preexisting model deployer ${NOFORMAT}mlflow_deployer"
  zenml model-registry register mlflow_registry --flavor=mlflow || \
    msg "${WARNING}Reusing preexisting model registry ${NOFORMAT}mlflow_registry"
  zenml experiment-tracker register mlflow_tracker  --flavor=mlflow || \
    msg "${WARNING}Reusing preexisting experiment tracker ${NOFORMAT}mlflow_tracker"
  zenml stack register mlflow_stack \
      -a default \
      -o default \
      -d mlflow_deployer \
      -r mlflow_registry \
      -e mlflow_tracker || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}mlflow_stack"

  zenml stack set mlflow_stack
}

pre_run () {
  zenml integration install tensorflow mlflow
}

pre_run_forced () {
  zenml integration install tensorflow mlflow -y
}
