#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install scikit-learn
  zenml integration install tensorflow
}

pre_run_forced () {
  zenml integration install scikit-learn -f
  zenml integration install tensorflow -f
}