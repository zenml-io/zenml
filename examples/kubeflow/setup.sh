#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml container-registry register local_registry  --type=default --uri=localhost:5000|| \
    msg "${WARNING}Reusing preexisting container registry ${NOFORMAT}local_registry, this might fail if port 5000 is blocked by another process."
  zenml orchestrator register kubeflow_orchestrator --type=kubeflow || \
    msg "${WARNING}Reusing preexisting orchestrator ${NOFORMAT}kubeflow_orchestrator"
  zenml stack register local_kubeflow_stack \
      -m local_metadata_store \
      -a local_artifact_store \
      -o kubeflow_orchestrator \
      -c local_registry || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_kubeflow_stack"

  zenml stack set local_kubeflow_stack

  zenml stack up
}

pre_run () {
  zenml integration install kubeflow
  zenml integration install sklearn
  zenml integration install tensorflow

  setup_stack
}

pre_run_forced () {
  zenml integration install kubeflow -f
  zenml integration install sklearn -f
  zenml integration install tensorflow -f

  setup_stack
}
