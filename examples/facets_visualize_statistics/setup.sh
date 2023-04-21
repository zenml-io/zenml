#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install facets sklearn
}

pre_run_forced () {
  zenml integration install facets sklearn -y
}
