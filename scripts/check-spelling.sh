#!/bin/sh -e
set -x

CODESPELL_SRC=${@:-"CODE-OF-CONDUCT.md CONTRIBUTING.md ROADMAP.md README.md RELEASE_NOTES.md src/ docs/book examples/ tests/"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
codespell -c -I .codespell-ignore-words -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code $CODESPELL_SRC
