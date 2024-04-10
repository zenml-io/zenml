#!/bin/bash

DB="sqlite"
DB_STARTUP_DELAY=30 # Time in seconds to wait for the database container to start

export ZENML_ANALYTICS_OPT_IN=false
export ZENML_DEBUG=true

# Use a temporary directory for the config path
export ZENML_CONFIG_PATH=/tmp/upgrade-tests

if [ -z "$1" ]; then
  echo "No argument passed, using default: $DB"
else
  DB="$1"
fi


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

function run_tests_for_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1
    # versions pre-templates and pre-init test flag
    # (zenml init --test allows for a non-interactive init)
    local PRE_TEMPLATE_VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0")
    local PRE_ARGS_VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0" "0.44.1" "0.44.3" "0.45.2" "0.45.3" "0.45.4" "0.45.5" "0.45.6" "0.46.0" "0.47.0" "0.50.0" "0.51.0" "0.52.0")

    echo "===== Testing version $VERSION ====="

    rm -rf test_starter template-starter

    # Check if VERSION is in PRE_TEMPLATE_VERSIONS
    if printf '%s\n' "${PRE_TEMPLATE_VERSIONS[@]}" | grep -q "^$VERSION$"; then
        copier copy -l --trust -r release/0.43.0 https://github.com/zenml-io/template-starter.git test_starter
    else
        mkdir test_starter
        zenml init --template starter --path test_starter --template-with-defaults <<< $'my@mail.com\n'
    fi

    cd test_starter

    echo "===== Installing sklearn integration ====="
    zenml integration export-requirements sklearn --output-file sklearn-requirements.txt
    uv pip install -r sklearn-requirements.txt
    rm sklearn-requirements.txt

    echo "===== Running starter template pipeline ====="
    if printf '%s\n' "${PRE_ARGS_VERSIONS[@]}" | grep -q "^$VERSION$"; then
        python3 run.py --no-cache
    else
        python3 run.py --feature-pipeline --training-pipeline --no-cache
    fi
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    zenml pipeline runs list

    cd ..
    rm -rf test_starter template-starter
    echo "===== Finished testing version $VERSION ====="
}

function test_upgrade_to_version() {
    set -e  # Exit immediately if a command exits with a non-zero status
    local VERSION=$1

    echo "===== Testing upgrade to version $VERSION ====="

    # (re)create a virtual environment
    rm -rf ".venv-upgrade"
    uv venv ".venv-upgrade"
    source ".venv-upgrade/bin/activate"

    # Install the specific version
    uv pip install -U setuptools wheel pip

    if [ "$VERSION" == "current" ]; then
        uv pip install -e ".[templates,server]"
        uv pip install importlib_metadata "pyyaml-include<2.0"
    else
        uv pip install "zenml[templates,server]==$VERSION"
        # handles unpinned sqlmodel dependency in older versions
        uv pip install "sqlmodel==0.0.8" "bcrypt==4.0.1" "pyyaml-include<2.0"
    fi

    # Get the major and minor version of Python
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    # Check if the Python version is 3.9 and VERSION is > 0.44.0
    if [[ "$PYTHON_VERSION" == "3.9" ]]; then
        case "$VERSION" in
            "0.44.1"|"0.44.3"|"0.45.2"|"0.45.3"|"0.45.4"|"0.45.5"|"0.45.6"|"0.46.0"|"0.47.0"|"0.50.0"|"0.51.0"|"0.52.0")
                uv pip install importlib_metadata
                ;;
        esac
    fi

    if [ "$DB" == "mysql" ] || [ "$DB" == "mariadb" ]; then
        # Use a database strategy for the database backup because this allows us
        # to catch database integrity errors in the backup process. Other strategies
        # save the database backup to a file or in memory and do not inject the
        # database backup into the database and that can hide errors in the backup
        # restoration process.
        export ZENML_STORE_BACKUP_STRATEGY=database
        export ZENML_STORE_BACKUP_DATABASE=zenml-backup

        zenml connect --url mysql://127.0.0.1/zenml --username root --password password
    fi

    # Run the tests for this version
    run_tests_for_version $VERSION

    deactivate
    rm -rf ".venv-upgrade"

    echo "===== Finished testing upgrade to version $VERSION ====="
}

function start_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "mysql" ]; then
        echo "===== Starting MySQL database ====="
        # run a mysql instance in docker
        docker run --name mysql --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8
        # mysql takes a while to start up
        sleep $DB_STARTUP_DELAY
        echo "===== Finished starting database ====="
    elif [ "$DB" == "mariadb" ]; then
        echo "===== Starting MariaDB database ====="
        # run a mariadb instance in docker
        docker run --name mariadb --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mariadb:10.6
        # mariadb takes a while to start up
        sleep $DB_STARTUP_DELAY
        echo "===== Finished starting database ====="
    else
        echo "===== Testing SQLite ====="
    fi
}

function stop_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "mysql" ]; then
        echo "===== Stopping MySQL database ====="
        docker stop mysql
    elif [ "$DB" == "mariadb" ]; then
        echo "===== Stopping MariaDB database ====="
        docker stop mariadb
    fi

    echo "===== Finished stopping database ====="
}

# List of versions to test
VERSIONS=("0.40.0" "0.40.3" "0.41.0" "0.43.0" "0.44.1" "0.44.3" "0.45.2" "0.45.3" "0.45.4" "0.45.5" "0.45.6" "0.46.0" "0.47.0" "0.50.0" "0.51.0" "0.52.0" "0.53.0" "0.53.1" "0.54.0" "0.54.1" "0.55.0" "0.55.1" "0.55.2" "0.55.3" "0.55.4" "0.55.5" "0.56.2")

# Start completely fresh
rm -rf "$ZENML_CONFIG_PATH"

pip install -U uv

# Start the database
start_db

for VERSION in "${VERSIONS[@]}"
do
    test_upgrade_to_version $VERSION
done

# Test the most recent migration with MySQL
test_upgrade_to_version "current"


# Start fresh again for this part
rm -rf "$ZENML_CONFIG_PATH"

# fresh database for sequential testing
stop_db
start_db

# Test sequential migrations across multiple versions
echo "===== TESTING SEQUENTIAL MIGRATIONS ====="
set -e

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

# Echo the sorted list of migration versions
echo "============================="
echo "TESTING MIGRATION_VERSIONS: ${MIGRATION_VERSIONS[@]}"
echo "============================="

for i in "${!MIGRATION_VERSIONS[@]}"; do
    test_upgrade_to_version ${MIGRATION_VERSIONS[$i]}
done

# Stop the database
stop_db

# Clean up
rm -rf "$ZENML_CONFIG_PATH"