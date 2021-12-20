#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  # "Currently run is not implemented for standard_interfaces due to manual loading of csv file!" -> exit code 42
  exit 38
  zenml integration install sklearn
  zenml integration install tensorflow
}

pre_run_forced () {
  # "Currently run is not implemented for standard_interfaces due to manual loading of csv file!" -> exit code 42
  exit 38
  zenml integration install sklearn -f
  zenml integration install tensorflow -f
}