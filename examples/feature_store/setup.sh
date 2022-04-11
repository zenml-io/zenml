#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
    zenml integration install feast
}

pre_run_forced () {
    zenml integration install feast -f
}
