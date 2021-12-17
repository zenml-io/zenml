#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  # "Currently run is not implemented for standard_interfaces due to manual loading of csv file!" -> exit code 42
  exit 42
  zenml integration install sklearn
  zenml integration install tensorflow
}