#!/usr/bin/env bash
set -e
set -x
set -o pipefail

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --changed-files)
      CHANGED_FILES="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      # unknown option
      shift
      ;;
  esac
done

# Default source directories
SRC="src/zenml tests examples"
SRC_NO_TESTS="src/zenml tests/harness"
TESTS_EXAMPLES="tests examples"

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

# Run ruff check on SRC_NO_TESTS
ruff check $SRC_NO_TESTS

# TODO: Fix docstrings in tests and examples and remove the `--extend-ignore D` flag
ruff check $TESTS_EXAMPLES --extend-ignore D --extend-exclude "*.ipynb"

# Flag check for skipping yamlfix
if [ "$OS" = "windows-latest" ]; then
    SKIP_YAMLFIX=true
else
    SKIP_YAMLFIX=false
    for arg in "$@"
    do
        if [ "$arg" = "--no-yamlfix" ]; then
            SKIP_YAMLFIX=true
            break
        fi
    done
fi

# checks for yaml formatting errors
if [ "$SKIP_YAMLFIX" = false ]; then
    yamlfix --check .github tests --exclude "dependabot.yml"
fi

# autoflake replacement: checks for unused imports and variables
ruff check $SRC --select F401,F841 --exclude "__init__.py" --exclude "*.ipynb" --isolated

ruff format $SRC --check

# check type annotations with mypy
# If CHANGED_FILES is not set, check all files in SRC_NO_TESTS
if [ -z "$CHANGED_FILES" ]; then
    mypy $SRC_NO_TESTS
else
    # Convert the space-separated list to an array
    IFS=' ' read -ra CHANGED_FILES_ARRAY <<< "$CHANGED_FILES"
    
    MYPY_FILES=()

    for file in "${CHANGED_FILES_ARRAY[@]}"; do
        if [[ $file == src/zenml* || $file == tests/harness* ]]; then
            MYPY_FILES+=("$file")
        fi
    done

    # Run mypy only if there are files to check
    if [ ${#MYPY_FILES[@]} -gt 0 ]; then
        mypy "${MYPY_FILES[@]}"
    else
        echo "No files to check with mypy."
    fi
fi