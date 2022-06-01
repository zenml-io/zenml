#!/bin/sh -e
set -x

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
pyspelling
