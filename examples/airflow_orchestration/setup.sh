#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml orchestrator register local_airflow --flavor=airflow || \
    msg "${WARNING}Reusing preexisting orchestrator ${NOFORMAT}local_airflow"
  zenml stack register local_airflow \
      -a default \
      -o local_airflow || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_airflow"

  zenml stack set local_airflow

  zenml stack up
}

pre_run () {
  zenml integration install airflow pytorch
  pip install apache-airflow-providers-docker torchvision
}

pre_run_forced () {
  zenml integration install airflow pytorch -y
  pip install apache-airflow-providers-docker torchvision
}
