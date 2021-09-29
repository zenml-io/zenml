#!/bin/sh -e
set -x

# Parse command line args
for i in "$@"
do
case $i in
    -s=*|--source=*)
    SOURCE="${i#*=}"
    ;;
    -v=*|--version=*)
    ZENML_VERSION="${i#*=}"
    ;;
    *)
            # unknown option
    ;;
esac
done

# If version passed in, then use a pinned version.
if [ -z "$ZENML_VERSION" ]
  then
    PACKAGE="zenml"
  else
    PACKAGE="zenml==${ZENML_VERSION}"
fi


# Optionally, install an integration. Leave empty otherwise.
EXTRAS = ""
EXAMPLE_NAME = "quickstart"

# Install and initialize.
pip install ${SOURCE} ${PACKAGE}
zenml example pull ${EXAMPLE_NAME}
cd zenml_examples/${EXAMPLE_NAME}
git init
zenml init

# Run the script
python run.py