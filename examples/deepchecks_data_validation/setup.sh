#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml data-validator register deepchecks_validator --flavor=deepchecks || \
    msg "${WARNING}Reusing preexisting data-validator ${NOFORMAT}deepchecks_validator"
  zenml stack register deepchecks_stack \
      -m default \
      -a default \
      -o default \
      -dv deepchecks_validator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}deepchecks_stack"

  zenml stack set deepchecks_stack
}

pre_run () {
  zenml integration install deepchecks sklearn
}

pre_run_forced () {
  zenml integration install deepchecks sklearn -f
}