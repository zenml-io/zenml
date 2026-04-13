#!/usr/bin/env bash
set -e
set -x
set -o pipefail

# Default source directories
SRC=${1:-"src/zenml tests examples"}
SRC_NO_TESTS=${1:-"src/zenml tests/harness"}
TESTS_EXAMPLES=${1:-"tests examples"}

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false
ruff check $SRC_NO_TESTS
# TODO: Fix docstrings in tests and examples and remove the `--extend-ignore D` flag
ruff check $TESTS_EXAMPLES --extend-ignore D --extend-exclude "*.ipynb"

pydoclint $SRC_NO_TESTS

# Flag checks for skipping optional linters
SKIP_YAMLFIX=false
SKIP_ZIZMOR=false

if [ "$OS" = "windows-latest" ]; then
    SKIP_YAMLFIX=true
fi

for arg in "$@"
do
    if [ "$arg" = "--no-yamlfix" ]; then
        SKIP_YAMLFIX=true
    elif [ "$arg" = "--no-zizmor" ]; then
        SKIP_ZIZMOR=true
    fi
done

# checks for yaml formatting errors
if [ "$SKIP_YAMLFIX" = false ]; then
    yamlfix --check .github tests -e "dependabot.yml" -e "workflows/release_prepare.yml" -e "workflows/release_finalize.yml" -e "workflows/integration-test-fast-services.yml" -e "workflows/integration-test-slow-services.yml"
fi

# checks for GitHub Actions security issues (SHA pinning, version mismatches, etc.)
if [ "$SKIP_ZIZMOR" = false ] && [ -d ".github/workflows" ]; then
    # Resolve GH_TOKEN: use existing env var, or try gh CLI
    if [ -z "$GH_TOKEN" ] && command -v gh &> /dev/null; then
        GH_TOKEN=$(gh auth token 2>/dev/null) || true
    fi

    if [ -n "$GH_TOKEN" ]; then
        export GH_TOKEN
        uvx zizmor --config=.github/zizmor.yml .github/workflows/
    else
        echo "⚠️  Skipping zizmor check: no GH_TOKEN and gh CLI not authenticated."
        echo "   Run: GH_TOKEN=\$(gh auth token) bash scripts/lint.sh"
    fi
fi

# autoflake replacement: checks for unused imports and variables
ruff check $SRC --select F401,F841 --exclude "__init__.py" --exclude "*.ipynb" --isolated

ruff format $SRC  --check

# check type annotations
mypy $SRC_NO_TESTS