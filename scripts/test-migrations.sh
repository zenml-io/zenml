#!/bin/bash

DB="sqlite"
DB_STARTUP_DELAY=30 # Time in seconds to wait for the database container to start

export ZENML_ANALYTICS_OPT_IN=false
export ZENML_DEBUG=true

# Use a temporary directory for the config path
export ZENML_CONFIG_PATH=/tmp/upgrade-tests

if [ -z "$1" ]; then
  echo "No database argument passed, using default: $DB"
else
  DB="$1"
fi

if [ -z "$2" ]; then
  echo "No migration type argument passed, defaulting to full"
  MIGRATION_TYPE="full"
else
  MIGRATION_TYPE="$2"
fi

# List of versions to test
VERSIONS=("0.40.3" "0.43.0" "0.44.3" "0.45.6" "0.47.0" "0.50.0" "0.51.0" "0.52.0" "0.53.1" "0.54.1" "0.55.5" "0.56.4" "0.57.1" "0.60.0" "0.61.0" "0.62.0" "0.63.0" "0.64.0" "0.65.0" "0.68.0" "0.70.0")

# Try to get the latest version using pip index
version=$(pip index versions zenml 2>/dev/null | grep -v YANKED | head -n1 | awk '{print $2}' | tr -d '()')

# Verify we got a version
if [ -z "$version" ]; then
    echo "Error: Could not find the latest version for zenml" >&2
    return 1
fi

LATEST_VERSION=$(echo $version | xargs)

if [[ ! " ${VERSIONS[@]} " =~ " ${LATEST_VERSION} " ]]; then
   VERSIONS+=("${LATEST_VERSION}")
fi

# Function to compare semantic versions
function version_compare() {
    local regex="^([0-9]+)\.([0-9]+)\.([0-9]+)(-([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?(\\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$"
    local ver1="$1"
    local ver2="$2"

    if [[ "$ver1" == "$ver2" ]]; then
        echo "="
        return
    fi

    if [[ $ver1 == "current" ]]; then
        echo ">"
        return
    fi

    if [[ $ver2 == "current" ]]; then
        echo "<"
        return
    fi

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

    echo "===== Testing version $VERSION ====="

    rm -rf test_starter template-starter

    # Check if the version supports templates via zenml init (> 0.43.0)
    if [ "$(version_compare "$VERSION" "0.43.0")" == ">" ]; then
        mkdir test_starter
        zenml init --template starter --path test_starter --template-with-defaults <<< $'my@mail.com\n'
    else
        copier copy -l --trust -r release/0.43.0 https://github.com/zenml-io/template-starter.git test_starter
    fi

    cd test_starter

    echo "===== Installing required integrations ====="
    # TODO: REMOVE BEFORE MERGE
    if [ "$VERSION" == "current" ]; then
        zenml integration export-requirements sklearn pandas --output-file integration-requirements.txt
    elif [ "$(version_compare "$VERSION" "0.66.0")" == "<" ]; then
        zenml integration export-requirements sklearn --output-file integration-requirements.txt
    else
        zenml integration export-requirements sklearn pandas --output-file integration-requirements.txt
    fi

    uv pip install -r integration-requirements.txt
    rm integration-requirements.txt

    echo "===== Running starter template pipeline ====="
    # Check if the version supports templates with arguments (> 0.52.0)
    if [ "$(version_compare "$VERSION" "0.52.0")" == ">" ]; then
        python3 run.py --feature-pipeline --training-pipeline --no-cache
        python3 run.py --feature-pipeline --training-pipeline # run with cache
    else
        python3 run.py --no-cache
        python3 run.py # run with cache
    fi
    # Add additional CLI tests here
    zenml version

    # Confirm DB works and is accessible
    ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list

    # The database backup and restore feature is available since 0.55.1.
    # However, it has been broken for various reasons up to and including
    # 0.57.0, so we skip this test for those versions.
    if [ "$VERSION" == "current" ] || [ "$(version_compare "$VERSION" "0.57.0")" == ">" ]; then
        echo "===== Testing database backup and restore (file dump) ====="

        pipelines_before_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)

        # Perform a DB backup and restore using a dump file
        rm -f /tmp/zenml-backup.sql
        zenml backup-database -s dump-file --location /tmp/zenml-backup.sql --overwrite
        zenml restore-database -s dump-file --location /tmp/zenml-backup.sql

        # Check that DB still works after restore and the content is the same
        pipelines_after_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)
        if [ "$pipelines_before_restore" != "$pipelines_after_restore" ]; then
            echo "----- Before restore -----"
            echo "$pipelines_before_restore"
            echo "----- After restore -----"
            echo "$pipelines_after_restore"
            echo "ERROR: database backup and restore (file dump) test failed!"
            exit 1
        fi

        # Run the pipeline again to check if the restored database is working
        echo "===== Running starter template pipeline after DB restore (file dump) ====="
        python3 run.py --feature-pipeline --training-pipeline --no-cache
        python3 run.py --feature-pipeline --training-pipeline # run with cache

        # For a mysql compatible database, perform a DB backup and restore using
        # the backup database
        if [ "$DB" == "mysql" ] || [ "$DB" == "mariadb" ]; then
            echo "===== Testing database backup and restore (backup database) ====="

            pipelines_before_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)

            # Perform a DB backup and restore
            zenml backup-database -s database --location zenml-backup --overwrite
            zenml restore-database -s database --location zenml-backup

            # Check that DB still works after restore and the content is the
            # same
            pipelines_after_restore=$(ZENML_LOGGING_VERBOSITY=INFO zenml pipeline runs list --size 5000)
            if [ "$pipelines_before_restore" != "$pipelines_after_restore" ]; then
                echo "----- Before restore -----"
                echo "$pipelines_before_restore"
                echo "----- After restore -----"
                echo "$pipelines_after_restore"
                echo "ERROR: database backup and restore (backup database) test failed!"
                exit 1
            fi

            # Run the pipeline again to check if the restored database is working
            echo "===== Running starter template pipeline after DB restore (backup database) ====="
            python3 run.py --feature-pipeline --training-pipeline --no-cache
            python3 run.py --feature-pipeline --training-pipeline # run with cache
        fi

    else
        echo "Skipping database backup and restore test for version $VERSION"
    fi

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
    else
        uv pip install "zenml[templates,server]==$VERSION"
        if [ "$(version_compare "$VERSION" "0.60.0")" == "<" ]; then
            # handles unpinned sqlmodel dependency in older versions
            uv pip install "sqlmodel==0.0.8" "bcrypt==4.0.1" "pyyaml-include<2.0" "numpy<2.0.0" "tenacity!=8.4.0"
        fi
    fi

    # Get the major and minor version of Python
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    # Check if the Python version is 3.9 and VERSION is > 0.44.0 and < 0.53.0
    if [[ "$PYTHON_VERSION" == "3.9" ]]; then
        if [ "$(version_compare "$VERSION" "0.44.0")" == ">" ] && [ "$(version_compare "$VERSION" "0.53.0")" == "<" ]; then
            # Install importlib_metadata for Python 3.9 and versions > 0.44.0 and < 0.53.0
            uv pip install importlib_metadata
        fi
    fi

    if [ "$DB" == "mysql" ] || [ "$DB" == "mariadb" ]; then

        if [ "$(version_compare "$VERSION" "0.68.1")" == ">" ]; then
            zenml login mysql://root:password@127.0.0.1/zenml
        else
            zenml connect --url mysql://root:password@127.0.0.1/zenml --username root --password password
        fi
    fi

    # Run the tests for this version
    run_tests_for_version "$VERSION"

    deactivate
    rm -rf ".venv-upgrade"

    echo "===== Finished testing upgrade to version $VERSION ====="
}

function start_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "sqlite" ]; then
        return
    fi

    stop_db    

    echo "===== Starting $DB database ====="
    if [ "$DB" == "mysql" ]; then
        # run a mysql instance in docker
        docker run --name mysql --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mysql:8
    elif [ "$DB" == "mariadb" ]; then
        # run a mariadb instance in docker
        docker run --name mariadb --rm -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=password mariadb:10.6
    fi

    # the database container takes a while to start up
    sleep $DB_STARTUP_DELAY
    echo "===== Finished starting $DB database ====="

}

function stop_db() {
    set -e  # Exit immediately if a command exits with a non-zero status

    if [ "$DB" == "sqlite" ]; then
        return
    fi

    echo "===== Stopping $DB database ====="

    if [ "$DB" == "mysql" ]; then
        docker stop mysql || true
    elif [ "$DB" == "mariadb" ]; then
        docker stop mariadb || true
    fi

    echo "===== Finished stopping $DB database ====="
}

# If testing the mariadb database, we remove versions older than 0.54.0 because
# we only started supporting mariadb from that version onwards
if [ "$DB" == "mariadb" ]; then
    MARIADB_VERSIONS=()
    for VERSION in "${VERSIONS[@]}"
    do
        if [ "$(version_compare "$VERSION" "0.54.0")" == "<" ]; then
            continue
        fi
        MARIADB_VERSIONS+=("$VERSION")
    done
    VERSIONS=("${MARIADB_VERSIONS[@]}")
fi

echo "Testing database: $DB"
echo "Testing versions: ${VERSIONS[@]}"
echo "Migration type: $MIGRATION_TYPE"

# Start completely fresh
rm -rf "$ZENML_CONFIG_PATH"

pip install -U uv

# Start the database
start_db

if [ "$MIGRATION_TYPE" == "full" ]; then
    for VERSION in "${VERSIONS[@]}"
    do
        test_upgrade_to_version "$VERSION"
    done

    # Test the most recent migration with MySQL
    test_upgrade_to_version "current"
else
    # Test the most recent migration with MySQL
    test_upgrade_to_version "current"

    # Start fresh again for this part
    rm -rf "$ZENML_CONFIG_PATH"

    # Fresh database for sequential testing
    stop_db
    start_db

    # Test random migrations across multiple versions
    echo "===== TESTING RANDOM MIGRATIONS ====="
    set -e

    function test_random_migrations() {
        set -e  # Exit immediately if a command exits with a non-zero status

        echo "===== TESTING RANDOM MIGRATIONS ====="

        # Randomly select versions for random migrations
        MIGRATION_VERSIONS=()
        while [ ${#MIGRATION_VERSIONS[@]} -lt 3 ]; do
            VERSION=${VERSIONS[$RANDOM % ${#VERSIONS[@]}]}
            if [[ ! " ${MIGRATION_VERSIONS[@]} " =~ " $VERSION " ]]; then
                MIGRATION_VERSIONS+=("$VERSION")
            fi
        done

        # Sort the versions in ascending order using semantic version comparison
        sorted_versions=()
        for version in "${MIGRATION_VERSIONS[@]}"; do
            inserted=false
            for i in "${!sorted_versions[@]}"; do
                if [ "$(version_compare "$version" "${sorted_versions[$i]}")" == "<" ]; then
                    sorted_versions=("${sorted_versions[@]:0:$i}" "$version" "${sorted_versions[@]:$i}")
                    inserted=true
                    break
                fi
            done
            if [ "$inserted" == false ]; then
                sorted_versions+=("$version")
            fi
        done
        MIGRATION_VERSIONS=("${sorted_versions[@]}")

        # Echo the sorted list of migration versions
        echo "============================="
        echo "TESTING MIGRATION_VERSIONS: ${MIGRATION_VERSIONS[@]}"
        echo "============================="

        for i in "${!MIGRATION_VERSIONS[@]}"; do
            test_upgrade_to_version "${MIGRATION_VERSIONS[$i]}"
        done

        # Test the most recent migration with MySQL
        test_upgrade_to_version "current"
    }

    test_random_migrations
fi

# Stop the database
stop_db

# Clean up
rm -rf "$ZENML_CONFIG_PATH"