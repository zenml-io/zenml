#!/bin/bash

DB="sqlite"
DB_STARTUP_DELAY=30 # Time in seconds to wait for the database container to start

export ZENML_ANALYTICS_OPT_IN=false
export ZENML_DEBUG=true

if [ -z "$1" ]; then
  echo "No argument passed, using default: $DB"
else
  DB="$1"
fi

function run_tests_for_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1
    # versions pre-templates and pre-init test flag
    # (zenml init --test allows for a non-interactive init)
    local PRE_TEMPLATE_VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0" "0.44.1" "0.44.3" "0.45.2" "0.45.3" "0.45.4" "0.45.5" "0.45.6" "0.46.0" "0.47.0")

    echo "===== Testing version $VERSION ====="

    # Check if VERSION is in PRE_TEMPLATE_VERSIONS
    if printf '%s\n' "${PRE_TEMPLATE_VERSIONS[@]}" | grep -q "^$VERSION$"; then
        copier copy -l --trust -r release/0.43.0 https://github.com/zenml-io/template-starter.git test_starter
    else
        mkdir test_starter
        zenml init --template starter --path test_starter --template-with-defaults --test
    fi

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



if [ "$1" == "mysql" ]; then
    echo "===== Testing MySQL ====="
    # run a mysql instance in docker
    docker run --name mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:latest
    # mysql takes a while to start up
    sleep $DB_STARTUP_DELAY
fi

# List of versions to test
VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0" "0.44.1" "0.44.3" "0.45.2" "0.45.3" "0.45.4" "0.45.5" "0.45.6" "0.46.0" "0.47.0" "0.50.0" "0.51.0" "0.52.0" "0.53.0" "0.53.1" "0.54.0" "0.54.1" "0.55.0" "0.55.1" "0.55.2" "0.55.3" "0.55.4")

# Start completely fresh
rm -rf ~/.config/zenml

for VERSION in "${VERSIONS[@]}"
do
    set -e  # Exit immediately if a command exits with a non-zero status
    # Create a new virtual environment
    python3 -m venv ".venv-$VERSION"
    source ".venv-$VERSION/bin/activate"

    # Install the specific version
    pip3 install -U pip setuptools wheel

    git checkout release/$VERSION
    pip3 install -e ".[templates,server]"
    # handles unpinned sqlmodel dependency in older versions
    pip3 install "sqlmodel==0.0.8" "bcrypt==4.0.1"

    # Get the major and minor version of Python
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    # Check if the Python version is 3.9 and VERSION is > 0.47.0
    if [[ "$PYTHON_VERSION" == "3.9" ]]; then
        case "$VERSION" in
            "0.47.0"|"0.50.0"|"0.51.0"|"0.52.0")
                pip3 install importlib_metadata
                ;;
        esac
    fi


    if [ "$1" == "mysql" ]; then
        zenml connect --url mysql://127.0.0.1/zenml --username root --password password
    fi

    # Run the tests for this version
    run_tests_for_version $VERSION

    if [ "$1" == "mysql" ]; then
        zenml disconnect
        sleep 5
    fi

    deactivate
done


# Test the most recent migration with MySQL
echo "===== TESTING CURRENT BRANCH ====="
set -e
python3 -m venv ".venv-current-branch"
source ".venv-current-branch/bin/activate"

pip3 install -U pip setuptools wheel
pip3 install -e ".[templates,server]"
pip3 install importlib_metadata

if [ "$1" == "mysql" ]; then
    zenml connect --url mysql://127.0.0.1/zenml --username root --password password
fi

run_tests_for_version current_branch_mysql

if [ "$1" == "mysql" ]; then
    zenml disconnect
    docker rm -f mysql
fi

deactivate

# Function to compare semantic versions
function version_compare() {
    local regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?(\\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$"
    local ver1="$1"
    local ver2="$2"

    if ! [[ $ver1 =~ $regex ]]; then
        echo "First argument does not conform to semantic version format" >&2
        return 1
    fi

    if ! [[ $ver2 =~ $regex ]]; then
        echo "Second argument does not conform to semantic version format" >&2
        return 1
    fi

    # Compare major, minor, and patch versions
    IFS='.' read -ra ver1_parts <<< "$ver1"
    IFS='.' read -ra ver2_parts <<< "$ver2"

    for ((i=0; i<3; i++)); do
        if ((ver1_parts[i] > ver2_parts[i])); then
            echo ">"
            return
        elif ((ver1_parts[i] < ver2_parts[i])); then
            echo "<"
            return
        fi
    done

    # Extend comparison to pre-release versions if necessary
    # This is a simplified comparison that may need further refinement
    if [[ -n ${ver1_parts[3]} && -z ${ver2_parts[3]} ]]; then
        echo "<"
        return
    elif [[ -z ${ver1_parts[3]} && -n ${ver2_parts[3]} ]]; then
        echo ">"
        return
    elif [[ -n ${ver1_parts[3]} && -n ${ver2_parts[3]} ]]; then
        if [[ ${ver1_parts[3]} > ${ver2_parts[3]} ]]; then
            echo ">"
            return
        elif [[ ${ver1_parts[3]} < ${ver2_parts[3]} ]]; then
            echo "<"
            return
        fi
    fi

    echo "="
}

# Start fresh again for this part
rm -rf ~/.config/zenml

# Test sequential migrations across multiple versions
echo "===== TESTING SEQUENTIAL MIGRATIONS ====="
set -e
python3 -m venv ".venv-sequential-migrations"
source ".venv-sequential-migrations/bin/activate"

pip3 install -U pip setuptools wheel

# Randomly select versions for sequential migrations
MIGRATION_VERSIONS=()
while [ ${#MIGRATION_VERSIONS[@]} -lt 3 ]; do
    VERSION=${VERSIONS[$RANDOM % ${#VERSIONS[@]}]}
    if [[ ! " ${MIGRATION_VERSIONS[@]} " =~ " $VERSION " ]]; then
        MIGRATION_VERSIONS+=("$VERSION")
    fi
done

# Sort the versions based on semantic versioning rules
IFS=$'\n' MIGRATION_VERSIONS=($(sort -t. -k 1,1n -k 2,2n -k 3,3n <<<"${MIGRATION_VERSIONS[*]}"))

for i in "${!MIGRATION_VERSIONS[@]}"; do
    # ... (existing code remains the same)
done

if [ "$1" == "mysql" ]; then
    zenml disconnect
    docker rm -f mysql
fi

deactivate
