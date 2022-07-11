#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install pigeon
  pip install fastai huggingface_hub
}

pre_run_forced () {
  zenml integration install pigeon -y
  pip install fastai huggingface_hub -Uqq
}
