#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install facets tensorflow
}

pre_run_forced () {
  zenml integration install facets tensorflow -y
}
