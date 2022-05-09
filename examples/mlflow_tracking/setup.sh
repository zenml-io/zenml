#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml experiment-tracker register mlflow_tracker  --type=mlflow || \
    msg "${WARNING}Reusing preexisting experiment tracker ${NOFORMAT}mlflow_tracker"
  zenml stack register mlflow_stack \
      -m default \
      -a default \
      -o default \
      -e mlflow_tracker || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}mlflow_stack"

  zenml stack set mlflow_stack
}

pre_run () {
  zenml integration install tensorflow
  zenml integration install mlflow
}

pre_run_forced () {
  zenml integration install tensorflow -y
  zenml integration install mlflow -y
}
