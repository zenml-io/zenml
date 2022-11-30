#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml experiment-tracker register neptune_tracker  --flavor=neptune || \
    msg "${WARNING}Reusing preexisting experiment tracker ${NOFORMAT}neptune_tracker"
  zenml stack register neptune_stack \
      -a default \
      -o default \
      -e neptune_tracker || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}neptune_stack"

  zenml stack set neptune_stack
}

pre_run () {
  zenml integration install tensorflow neptune
}

pre_run_forced () {
  zenml integration install tensorflow neptune -y
}
