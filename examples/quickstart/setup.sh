#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install scikit-learn
}

pre_run_forced () {
  zenml integration install scikit-learn -f
}