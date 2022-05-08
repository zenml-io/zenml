#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  pip install torchvision
  zenml integration install pytorch
}

pre_run_forced () {
  pip install torchvision
  zenml integration install pytorch -f
}
