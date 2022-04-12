#!/usr/bin/env bash

set -Eeo pipefail

setup_stack () {
zenml secrets-manager register aws_secrets_manager -t local
zenml stack register secrets_stack -m default -o default -a default -x aws_secrets_manager
zenml stack set secrets_stack
zenml secret register example_secret -k example_secret_key -v example_secret_value
}

pre_run () {
  zenml integration install aws
}

pre_run_forced () {
  zenml integration install aws -f
}


post_run () {
  # cleanup the secret manager
  zenml secret delete example_secret -k example_secret_key -v example_secret_value
}
