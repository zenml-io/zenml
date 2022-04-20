#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install pytorch seldon
  pip install torchvision
}

pre_run_forced () {
  zenml integration install pytorch seldon -f
  pip install torchvision
}
