#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml orchestrator register airflow_orchestrator --type=airflow || \
    msg "${WARNING}Reusing preexisting orchestrator ${NOFORMAT}airflow_orchestrator"
  zenml stack register local_airflow_stack \
      -m local_metadata_store \
      -a local_artifact_store \
      -o airflow_orchestrator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_airflow_stack"

  zenml stack set local_airflow_stack

  zenml stack up
}

pre_run () {
  zenml integration install airflow sklearn

  setup_stack
}

pre_run_forced () {
  zenml integration install airflow sklearn -f

  setup_stack
}