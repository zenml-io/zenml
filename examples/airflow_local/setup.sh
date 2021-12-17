#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install airflow
  zenml integration install sklearn
  zenml integration install tensorflow
  zenml integration install beam
}