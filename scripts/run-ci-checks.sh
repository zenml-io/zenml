#!/usr/bin/env bash
set -e
set -x

scripts/lint.sh
scripts/docstring.sh
