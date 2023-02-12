#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml experiment-tracker register mlflow_tracker  --flavor=mlflow || \
    msg "${WARNING}Reusing preexisting experiment tracker ${NOFORMAT}mlflow_tracker"
  zenml stack register mlflow_stack \
      -a default \
      -o default \
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
