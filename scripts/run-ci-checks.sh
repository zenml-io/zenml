#!/usr/bin/env bash
set -e
set -x

scripts/lint.sh
scripts/check-spelling.sh
scripts/docstring.sh
