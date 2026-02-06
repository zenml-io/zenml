#!/bin/sh -e

INTEGRATIONS=no
PIP_ARGS=
UPGRADE_ALL=no

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Install ZenML in development mode with optional integrations.

OPTIONS:
    -i, --integrations yes|no    Install integrations (default: no)
    -s, --system                 Install packages system-wide instead of in virtual environment
    -u, --upgrade-all           Uninstall existing ZenML, clear caches, and install latest versions
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

install_zenml() {
    echo "📦 Installing ZenML in editable mode..."
    
    # Build upgrade arguments based on UPGRADE_ALL flag
    upgrade_args=""
    if [ "$UPGRADE_ALL" = "yes" ]; then
        upgrade_args="--upgrade --force-reinstall"
        echo "🔄 Using --upgrade --force-reinstall to get latest versions"
    fi
    
    # install ZenML in editable mode
    uv pip install $PIP_ARGS $upgrade_args -e ".[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]"
    
    echo "✅ ZenML installation completed"
}

install_integrations() {
    echo "🔌 Installing ZenML integrations..."

    # figure out the python version
    python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

    ignore_integrations="feast label_studio bentoml seldon pycaret skypilot_aws skypilot_gcp skypilot_azure skypilot_kubernetes skypilot_lambda pigeon prodigy argilla vllm"

    # Ignore tensorflow and deepchecks only on Python 3.12 and 3.13
    if [ "$python_version" = "3.12" ] || [ "$python_version" = "3.13" ]; then
        ignore_integrations="$ignore_integrations tensorflow deepchecks"
    fi

    # TODO: Revisit once pytorch Windows support stabilises.
    # torch DLL loading on Windows CI is unreliable (OSError / FileNotFoundError
    # at import time). Tracked in: https://github.com/zenml-io/zenml/issues/4471
    os_name=$(python -c "import platform; print(platform.system())")
    if [ "$os_name" = "Windows" ]; then
        ignore_integrations="$ignore_integrations pytorch neural_prophet pytorch_lightning"
    fi
    
    # turn the ignore integrations into a list of --ignore-integration args
    ignore_integrations_args=""
    for integration in $ignore_integrations; do
        ignore_integrations_args="$ignore_integrations_args --ignore-integration $integration"
    done

    # install basic ZenML integrations
    zenml integration export-requirements \
        --output-file integration-requirements.txt \
        $ignore_integrations_args

    # Handle package pins based on upgrade mode
    if [ "$UPGRADE_ALL" = "yes" ]; then
        echo "🔄 Using latest versions for integration dependencies"
        # When upgrading, use minimum versions to allow latest compatible
        echo "" >> integration-requirements.txt
        echo "pyyaml>=6.0.1" >> integration-requirements.txt
        echo "pyopenssl" >> integration-requirements.txt
        echo "typing-extensions" >> integration-requirements.txt
        echo "maison<2" >> integration-requirements.txt
    else
        # Original behavior with specific pins
        echo "" >> integration-requirements.txt
        echo "pyyaml>=6.0.1" >> integration-requirements.txt
        echo "pyopenssl" >> integration-requirements.txt
        echo "typing-extensions" >> integration-requirements.txt
        echo "maison<2" >> integration-requirements.txt
    fi
    
    echo "-e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]" >> integration-requirements.txt

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
