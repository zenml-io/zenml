#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml data-validator register evidently_validator --flavor=evidently || \
    msg "${WARNING}Reusing preexisting data-validator ${NOFORMAT}evidently_validator"
  zenml stack register evidently_stack \
      -m default \
      -a default \
      -o default \
      -dv evidently_validator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}evidently_stack"

  zenml stack set evidently_stack
}

pre_run () {
  zenml integration install evidently sklearn
}

pre_run_forced () {
  zenml integration install evidently sklearn -y
}
