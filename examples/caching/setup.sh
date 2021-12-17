#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install beam
  zenml integration install tensorflow
}