#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install graphviz
  zenml integration install tensorflow
}

pre_run_forced () {
  zenml integration install graphviz -f
  zenml integration install tensorflow -f
}