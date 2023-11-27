#!/bin/bash

function run_tests_for_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1

    echo "===== Testing version $VERSION ====="
    # Initialize zenml with the appropriate template
    # hardcoded to 0.43.0 since this is the latest template-starter repo
    # release tag
    git clone -b "release/0.43.0" https://github.com/zenml-io/template-starter
    copier copy template-starter/ test_starter --trust --defaults
    cd test_starter

    export ZENML_ANALYTICS_OPT_IN=false
    export ZENML_DEBUG=true

    echo "===== Installing sklearn integration ====="
    zenml integration install sklearn -y

    echo "===== Running starter template pipeline ====="
    python3 run.py
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    zenml pipeline runs list

    cd ..
    rm -rf test_starter template-starter
    echo "===== Finished testing version $VERSION ====="
}

# List of versions to test
VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0" "0.44.1" "0.44.3" "0.45.2" "0.45.3" "0.45.4" "0.45.5" "0.45.6" "0.46.0" "0.47.0")

for VERSION in "${VERSIONS[@]}"
do
    set -e  # Exit immediately if a command exits with a non-zero status
    # Create a new virtual environment
    python3 -m venv ".venv-$VERSION"
    source ".venv-$VERSION/bin/activate"

    # Install the specific version
    pip3 install -U pip setuptools wheel
    pip3 install "zenml[templates,server]==$VERSION"
    # handles unpinned sqlmodel dependency in older versions
    pip3 install "sqlmodel==0.0.8" importlib_metadata

    # Run the tests for this version
    run_tests_for_version $VERSION

    deactivate
done

# Test the version of the current branch
set -e
python3 -m venv ".venv-current-branch"
source ".venv-current-branch/bin/activate"

pip3 install -U pip setuptools wheel
pip install -e ".[templates,server]"
pip3 install importlib_metadata

run_tests_for_version current_branch

deactivate
