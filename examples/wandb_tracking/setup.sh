#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install tensorflow
  zenml integration install wandb
}

pre_run_forced () {
  zenml integration install tensorflow -f
  zenml integration install wandb -f
}