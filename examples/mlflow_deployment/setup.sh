#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
  zenml model-deployer register mlflow --type=mlflow
  zenml stack register local_with_mlflow -m default -a default -o default -d mlflow
  zenml stack set local_with_mlflow
}

pre_run () {
  zenml integration install tensorflow
  zenml integration install mlflow
}

pre_run_forced () {
  zenml integration install tensorflow -f
  zenml integration install mlflow -f
}

post_run () {
  # cleanup the last local ZenML daemon started by the example
  pkill -n -f zenml.services.local.local_daemon_entrypoint
}
