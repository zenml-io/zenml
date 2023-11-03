#!/bin/bash

function run_tests_for_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1

    # Initialize zenml with the appropriate template
    git clone -b "release/0.43.0" https://github.com/zenml-io/template-starter
    copier copy template-starter/ test_starter --trust --defaults
    cd test_starter

    zenml integration install sklearn -y
    python3 run.py
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    zenml pipeline runs list >> dump.txt && echo "Success listing pipeline runs on $VERSION"

    cd ..
    rm -rf test_starter template_starter
}

# List of versions to test
# VERSIONS=("0.39.1" "0.44.3" "0.45.3" "0.45.6")
VERSIONS=("0.45.5" "0.45.6")

for VERSION in "${VERSIONS[@]}"
do
    # Create a new virtual environment
    python3 -m venv ".venv-$VERSION"
    source ".venv-$VERSION/bin/activate"

    # Install the specific version
    pip3 install -U pip
    pip3 install "zenml[templates]==$VERSION"

    # Run the tests for this version
    run_tests_for_version $VERSION

    deactivate
done
