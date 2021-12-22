#!/bin/sh -e
set -x

SRC=${1:-"src/zenml tests examples"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
codespell -c -I .codespell-ignore-words -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code CODE-OF-CONDUCT.md CONTRIBUTING.md ROADMAP.md README.md RELEASE_NOTES.md src/ docs/book examples/