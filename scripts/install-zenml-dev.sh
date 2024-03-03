#!/bin/sh -e

INTEGRATIONS=no

parse_args () {
    while [ $# -gt 0 ]; do
        case $1 in
            -i|--integrations)
                INTEGRATIONS="$2"
                shift # past argument
                shift # past value
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

    touch zenml_requirements.txt
    echo "-e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,mlstacks]" >> zenml_requirements.txt

    cp zenml_requirements.txt zenml_requirements.in
    uv pip compile zenml_requirements.in -o zenml_requirements-compiled.txt

    pip install -r zenml_requirements-compiled.txt
    rm zenml_requirements.txt
    rm zenml_requirements.in
}

install_integrations() {

    # figure out the python version
    python_version=$(python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

    ignore_integrations="feast label_studio bentoml seldon kserve pycaret skypilot_aws skypilot_gcp skypilot_azure"
    # if python version is 3.11, exclude all integrations depending on kfp
    # because they are not yet compatible with python 3.11
    if [ "$python_version" = "3.11" ]; then
        ignore_integrations="$ignore_integrations kubeflow tekton gcp"
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
    echo "-e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,mlstacks]" >> integration-requirements.txt
    cp integration-requirements.txt integration-requirements.in

    pip install uv

    uv pip compile integration-requirements.in -o integration-requirements-compiled.txt

    pip install -r integration-requirements-compiled.txt
    rm integration-requirements.txt
    rm integration-requirements.in
    rm integration-requirements-compiled.txt
}


set -x
set -e

export ZENML_DEBUG=1
export ZENML_ANALYTICS_OPT_IN=false

parse_args "$@"

python -m pip install --upgrade pip setuptools wheel uv

install_zenml

# install integrations, if requested
if [ "$INTEGRATIONS" = yes ]; then
    install_integrations
fi
