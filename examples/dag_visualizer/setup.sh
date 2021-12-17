#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install graphviz
  zenml integration install tensorflow
  zenml integration install beam
}