#!/usr/bin/env bash
set -e
set -x

SRC=${1:-"src/zenml tests"}
SRC_NO_TESTS=${1:-"src/zenml"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
flake8 $SRC
autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place $SRC --exclude=__init__.py --check
isort $SRC scripts --check-only
black $SRC  --check
interrogate $SRC_NO_TESTS -c pyproject.toml
mypy $SRC_NO_TESTS
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code CODE-OF-CONDUCT.md
codespell  -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code CONTRIBUTING.md
codespell  -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code ROADMAP.md
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code README.md
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code RELEASE_NOTES.md
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code src/
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code docs/book
codespell -c -f -i 0 --builtin clear,rare,en-GB_to_en-US,names,code examples/
