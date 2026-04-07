#!/bin/sh -e

INTEGRATIONS=no
PIP_ARGS=
UPGRADE_ALL=no
EXPORT_REQUIREMENTS_FILE=
TARGET_PYTHON_VERSION=
TARGET_OS=
TARGET_PLATFORM=
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEV_REQUIREMENTS_HELPER="$SCRIPT_DIR/install_dev_requirements.py"

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Install ZenML in development mode with optional integrations.

OPTIONS:
    -i, --integrations yes|no    Install integrations (default: no)
    -s, --system                 Install packages system-wide instead of in virtual environment
    -u, --upgrade-all           Uninstall existing ZenML, clear caches, and install latest versions
    --export-requirements-file PATH
                                Export resolved requirements to PATH and exit
    --target-python-version VERSION
                                Target Python version for requirements export
    --target-os NAME            Target OS for requirements export
    --target-platform TAG      Explicit target platform for requirements export
    -h, --help                  Show this help message

EXAMPLES:
    # Basic installation
    $0
    
    # Install with integrations
    $0 --integrations yes
    
    # Force reinstall with latest versions of all dependencies
    $0 --upgrade-all --integrations yes
    
    # System-wide installation with latest versions
    $0 --system --upgrade-all

    # Export Linux Python 3.13 requirements without installing anything
    $0 --integrations yes --export-requirements-file requirements.txt \
       --target-python-version 3.13 --target-os Linux \
       --target-platform x86_64-manylinux_2_35

NOTES:
    - The --upgrade-all flag will uninstall existing ZenML installation and clear all caches
    - This ensures you get the latest compatible versions of all dependencies
    - Use this when you want to refresh your environment with the newest packages

EOF
}

parse_args () {
    while [ $# -gt 0 ]; do
        case $1 in
            -i|--integrations)
                INTEGRATIONS="$2"
                shift # past argument
                shift # past value
                ;;
            -s|--system)
                PIP_ARGS="--system"
                shift # past argument
                ;;
            -u|--upgrade-all)
                UPGRADE_ALL="yes"
                shift # past argument
                ;;
            --export-requirements-file)
                EXPORT_REQUIREMENTS_FILE="$2"
                shift # past argument
                shift # past value
                ;;
            --target-python-version)
                TARGET_PYTHON_VERSION="$2"
                shift # past argument
                shift # past value
                ;;
            --target-os)
                TARGET_OS="$2"
                shift # past argument
                shift # past value
                ;;
            --target-platform)
                TARGET_PLATFORM="$2"
                shift # past argument
                shift # past value
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*|--*)
                echo "Unknown option $1"
                show_help
                exit 1
                ;;
            *)
                shift # past argument
                ;;
        esac
    done
}

clean_and_uninstall() {
    echo "🧹 Cleaning existing ZenML installation and clearing caches..."
    
    # Uninstall ZenML (if installed) and clear pip cache
    uv pip uninstall $PIP_ARGS zenml || true
    
    # Clear uv cache to ensure fresh downloads
    uv cache clean || true
    
    # Clear pip cache as well (in case pip was used previously)
    python -m pip cache purge 2>/dev/null || true
    
    echo "✅ Cleanup completed"
}

editable_install_spec() {
    python "$DEV_REQUIREMENTS_HELPER" editable-spec
}

resolve_target_python_version() {
    if [ -n "$TARGET_PYTHON_VERSION" ]; then
        echo "$TARGET_PYTHON_VERSION"
    else
        python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
    fi
}

resolve_target_os() {
    if [ -n "$TARGET_OS" ]; then
        echo "$TARGET_OS"
    else
        python -c "import platform; print(platform.system())"
    fi
}

export_requirements() {
    if [ -z "$EXPORT_REQUIREMENTS_FILE" ]; then
        echo "Missing --export-requirements-file"
        exit 1
    fi

    python_version=$(resolve_target_python_version)
    os_name=$(resolve_target_os)
    target_platform_args=""
    if [ -n "$TARGET_PLATFORM" ]; then
        target_platform_args="--target-platform $TARGET_PLATFORM"
    fi

    echo "📝 Exporting resolved ZenML requirements to $EXPORT_REQUIREMENTS_FILE..."
    # shellcheck disable=SC2086
    python "$DEV_REQUIREMENTS_HELPER" write-compiled-requirements \
        --output-file "$EXPORT_REQUIREMENTS_FILE" \
        --python-version "$python_version" \
        --target-os "$os_name" \
        $target_platform_args \
        --include-integrations "$INTEGRATIONS"

    echo "✅ Requirements export completed"
}

install_zenml() {
    echo "📦 Installing ZenML in editable mode..."
    
    # Build upgrade arguments based on UPGRADE_ALL flag
    upgrade_args=""
    if [ "$UPGRADE_ALL" = "yes" ]; then
        upgrade_args="--upgrade --force-reinstall"
        echo "🔄 Using --upgrade --force-reinstall to get latest versions"
    fi
    
    # install ZenML in editable mode
    uv pip install $PIP_ARGS $upgrade_args -e "$(editable_install_spec)"
    
    echo "✅ ZenML installation completed"
}

install_integrations() {
    echo "🔌 Installing ZenML integrations..."

    python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    os_name=$(python -c "import platform; print(platform.system())")

    python "$DEV_REQUIREMENTS_HELPER" write-integration-input \
        --output-file integration-requirements.txt \
        --python-version "$python_version" \
        --target-os "$os_name" \
        --include-project-spec yes

    # Build upgrade arguments based on UPGRADE_ALL flag
    upgrade_args=""
    if [ "$UPGRADE_ALL" = "yes" ]; then
        upgrade_args="--upgrade --force-reinstall"
        echo "🔄 Using --upgrade --force-reinstall for integration dependencies"
    fi

    uv pip install $PIP_ARGS $upgrade_args -r integration-requirements.txt
    rm integration-requirements.txt
    
    echo "✅ Integration installation completed"

    # https://github.com/Kludex/python-multipart/pull/166
    # There is an install conflict between multipart and python_multipart
    # which causes our server to fail in case both are installed. We
    # need to uninstall this library for now until the changes make it into
    # fastapi and then need to bump the fastapi version to resolve this.
    uv pip uninstall $PIP_ARGS multipart
}

set -x
set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

parse_args "$@"

if [ -n "$EXPORT_REQUIREMENTS_FILE" ]; then
    export_requirements
    exit 0
fi

# Clean and upgrade tooling packages if upgrading all
if [ "$UPGRADE_ALL" = "yes" ]; then
    echo "🚀 Upgrading all dependencies to latest versions..."
    clean_and_uninstall
    python -m pip install --upgrade --force-reinstall wheel pip uv
else
    python -m pip install --upgrade wheel pip uv
fi

install_zenml

# install integrations, if requested
if [ "$INTEGRATIONS" = yes ]; then
    install_integrations
fi
