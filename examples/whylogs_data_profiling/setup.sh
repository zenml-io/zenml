#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml data-validator register whylogs_validator --flavor=whylogs || \
    msg "${WARNING}Reusing preexisting data-validator ${NOFORMAT}whylogs_validator"
  zenml stack register whylogs_stack \
      -m default \
      -a default \
      -o default \
      -dv whylogs_validator || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}whylogs_stack"

  zenml stack set whylogs_stack
}


pre_run () {
  zenml integration install whylogs sklearn
}

pre_run_forced () {
  zenml integration install whylogs sklearn -y
}
