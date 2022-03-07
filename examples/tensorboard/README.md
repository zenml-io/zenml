# Visualize model statistics with Tensorboard

This example features a pipeline that trains a Keras model that logs Tensorboard
information that can be visualized after the pipeline run is over.

## Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```bash
# Install python dependencies
pip install zenml

# Install ZenML integrations
zenml integration install tensorflow

# Pull the tensorboard example
zenml example pull tensorboard
cd zenml_examples/tensorboard

# Initialize a ZenML repository
zenml init
```
### Run the project
Now we're ready. Execute:

```bash
python run.py
```

### Clean up
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

## SuperQuick `tensorboard` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run tensorboard
```
