#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install feast
  redis-server --daemonize yes
}

pre_run_forced () {
  zenml integration install feast -y
  redis-server --daemonize yes
}
