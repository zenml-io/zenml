#!/bin/bash

# install helper packages

uv pip install pyupgrade
uv pip install autoflake

# run py-upgrade recursively to all nested .py files

find src -name '*.py' -print0 | xargs -0 -n1 python -m pyupgrade --py310-plus

# run autoflake to remove dangling imports

autoflake --remove-all-unused-imports --in-place --recursive src

# run ruff check to verify imports are fixed

ruff check core --select F401
