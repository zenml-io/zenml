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
    pip install -e .[server,templates,terraform,secrets-aws,secrets-gcp,secrets-azure,secrets-hashicorp,s3fs,gcsfs,adlfs,dev,mlstacks]
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

    # Sort the original requirements file
    sort integration-requirements.txt > integration-requirements-sorted.txt

    # Calculate the line count of the sorted file and divide by 2 (using bc for floating to integer conversion)
    total_lines=$(wc -l < integration-requirements-sorted.txt)
    half_lines=$(echo "$total_lines / 2" | bc)

    # Split the sorted file into two parts
    split -l $half_lines integration-requirements-sorted.txt temp_part_

    # Rename the split files for clarity
    mv temp_part_aa part1.txt
    mv temp_part_ab part2.txt

    # Install requirements from the first part, then delete the file
    pip install -r part1.txt
    rm part1.txt

    # Install requirements from the second part, then delete the file
    pip install -r part2.txt
    rm part2.txt

    # Finally, delete the original sorted file
    rm integration-requirements-sorted.txt

    # install langchain separately
    zenml integration install -y langchain
}


set -x
set -e

parse_args "$@"

python -m pip install --upgrade pip

install_zenml

# install integrations, if requested
if [ "$INTEGRATIONS" = yes ]; then
    install_integrations
    # refresh the ZenML installation after installing integrations
    install_zenml
fi
