#!/usr/bin/env bash
set -x

# Initialize default source directories
default_src="src/zenml tests examples docs/mkdocstrings_helper.py scripts"
# Initialize SRC as an empty string
SRC=""

# Initialize SKIP_YAMLFIX and SKIP_UPGRADE as false
SKIP_YAMLFIX=false
SKIP_UPGRADE=true

# Process arguments
for arg in "$@"
do
    # Check for the --no-yamlfix and --no-upgrade flags
    if [ "$arg" = "--no-yamlfix" ]; then
        SKIP_YAMLFIX=true
    elif [ "$arg" = "--no-upgrade" ]; then
        SKIP_UPGRADE=true
    else
        # If it's not the flag, treat it as a source directory
        # Append the argument to SRC, separated by space
        if [ -z "$SRC" ]; then
            SRC="$arg"
        else
            SRC="$SRC $arg"
        fi
    fi
done

# Check for ruff and yamlfix versions
if [ "$SKIP_UPGRADE" = false ]; then
    RED='\033[0;31m'
    NC='\033[0m'
    
    pip install uv -q
    uv_output=$(uv pip install ".[dev]" --dry-run --upgrade --system 2>&1 | grep "+")
    ruff_version_change=$(echo "$uv_output" | grep "+ ruff")
    yamlfix_version_change=$(echo "$uv_output" | grep "+ yamlfix")
    
    if [ -n "$ruff_version_change" ]; then
        echo "${RED}ruff version is outdated and might lead to CI failures. Consider upgrading to ${ruff_version_change:3}.${NC}"
    fi
    if [ -n "$yamlfix_version_change" ]; then
        echo "${RED}yamlfix version is outdated and might lead to CI failures. Consider upgrading to ${yamlfix_version_change:3}.${NC}"
    fi
fi

# If no source directories were provided, use the default
if [ -z "$SRC" ]; then
    SRC="$default_src"
fi

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

# autoflake replacement: removes unused imports and variables
ruff check $SRC --select F401,F841 --fix --exclude "__init__.py" --isolated

# sorts imports
ruff check $SRC --select I --fix --ignore D
ruff format $SRC

# standardizes / formats CI yaml files
if [ "$SKIP_YAMLFIX" = false ]; then
    yamlfix .github tests --exclude "dependabot.yml"
fi