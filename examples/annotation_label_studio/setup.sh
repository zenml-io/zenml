#!/usr/bin/env bash

set -Eeo pipefail

pre_run () {
  zenml integration install label_studio
  pip install fastai huggingface_hub
}

pre_run_forced () {
  zenml integration install label_studio -y
  pip install fastai huggingface_hub -Uqq
}
