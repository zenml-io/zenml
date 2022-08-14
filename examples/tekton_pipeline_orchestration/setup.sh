#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml container-registry register local_registry  --flavor=default --uri=localhost:5000|| \
    msg "${WARNING}Reusing preexisting container registry ${NOFORMAT}local_registry, this might fail if port 5000 is blocked by another process."
  zenml orchestrator register local_tekton_stack --flavor=tekton || \
    msg "${WARNING}Reusing preexisting orchestrator ${NOFORMAT}local_tekton_stack"
  zenml stack register local_tekton_stack \
      -m default \
      -a default \
      -o local_tekton_orchestrator \
      -c local_registry || \
    msg "${WARNING}Reusing preexisting stack ${NOFORMAT}local_tekton_stack"

  zenml stack set local_tekton_stack

  zenml stack up
}

pre_run () {
  zenml integration install tekton tensorflow
}

pre_run_forced () {
  zenml integration install tekton tensorflow -y
}

post_run () {
  # cleanup the last local ZenML daemon started by the example
  pkill -n -f zenml.services.local.local_daemon_entrypoint || true
}
