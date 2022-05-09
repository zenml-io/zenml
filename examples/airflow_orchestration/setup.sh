#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml orchestrator register airflow_orchestrator --flavor=airflow || \
    msg "${WARNING}Reusing preexisting orchestrator ${NOFORMAT}airflow_orchestrator"
  zenml stack register local_airflow_stack \
      -m default \
      -a default \
      -o airflow_orchestrator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_airflow_stack"

  zenml stack set local_airflow_stack

  zenml stack up
}

pre_run () {
  zenml integration install airflow
}

pre_run_forced () {
  zenml integration install airflow -y
}
