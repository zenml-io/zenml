#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml data-validator register great_expectations_validator --flavor=great_expectations || \
    msg "${WARNING}Reusing preexisting data-validator ${NOFORMAT}great_expectations_validator"
  zenml stack register great_expectations_stack \
      -m default \
      -a default \
      -o default \
      -dv great_expectations_validator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}great_expectations_stack"

  zenml stack set great_expectations_stack
}

pre_run () {
  zenml integration install sklearn great_expectations
}

pre_run_forced () {
  zenml integration install sklearn great_expectations -f
}
