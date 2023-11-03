#!/bin/bash

function run_tests_for_version() {
    local VERSION=$1

    # Initialize zenml with the appropriate template
    if zenml init --template supported > zenml init --template starter --template-with-defaults; then
        echo "Used the supported template"
    else
        git clone -b "release/$VERSION" https://github.com/zenml-io/template-starter
    fi

    python3 run.py
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    zenml pipeline runs list >> dump.txt && echo "expected success of list pipeline runs on $VERSION"
}

# List of versions to test
VERSIONS=("0.39.1" "0.44.3" "0.45.3" "0.45.6")

for VERSION in "${VERSIONS[@]}"
do
    # Create a new virtual environment
    python3 -m venv ".venv$VERSION"
    source ".venv$VERSION/bin/activate"
    
    # Install the specific version
    pip3 install "zenml==$VERSION"
    
    # Run the tests for this version
    run_tests_for_version $VERSION
    
    deactivate
done
