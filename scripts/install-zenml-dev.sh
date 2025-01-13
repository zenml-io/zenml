#!/bin/sh -e

INTEGRATIONS=no
PIP_ARGS=

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
            -*|--*)
                echo "Unknown option $1"
                exit 1
                ;;
            *)
                shift # past argument
                ;;
        esac
    done
}

install_zenml() {
    # install ZenML in editable mode
    uv pip install $PIP_ARGS -e ".[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]"
}

install_integrations() {

    # figure out the python version
    python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

    ignore_integrations="feast label_studio bentoml seldon pycaret skypilot_aws skypilot_gcp skypilot_azure pigeon prodigy argilla"

    # Ignore tensorflow and deepchecks only on Python 3.12
    if [ "$python_version" = "3.12" ]; then
        ignore_integrations="$ignore_integrations tensorflow deepchecks"
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

    # pin pyyaml>=6.0.1
    echo "" >> integration-requirements.txt
    echo "pyyaml>=6.0.1" >> integration-requirements.txt
    echo "pyopenssl" >> integration-requirements.txt
    echo "typing-extensions" >> integration-requirements.txt
    echo "-e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,connectors-aws,connectors-gcp,connectors-azure,azureml,sagemaker,vertex]" >> integration-requirements.txt

    # workaround to make yamlfix work
    echo "maison<2" >> integration-requirements.txt

    uv pip install $PIP_ARGS -r integration-requirements.txt
    rm integration-requirements.txt

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

python -m pip install --upgrade setuptools wheel pip uv

install_zenml

# install integrations, if requested
if [ "$INTEGRATIONS" = yes ]; then
    install_integrations
fi
