#!/usr/bin/env bash

set -Eeo pipefail

# Optional - not all examples will need to set up a specific stack
setup_stack () {
  # register stack components, register and set stack and perform other stack related operations
}

pre_run () {
  zenml integration install <INSERT ALL REQUIRED ZENML INTEGRATIONS>
}

pre_run_forced () {
  zenml integration install <INSERT ALL REQUIRED ZENML INTEGRATIONS> -y
}

# Optional- not all examples need to clean up daemons
post_run () {
  # clean up after an example run
}
