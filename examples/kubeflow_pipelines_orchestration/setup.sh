#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install kubeflow tensorflow tensorboard
}

pre_run_forced () {
  zenml integration install kubeflow tensorflow tensorboard -y
}
