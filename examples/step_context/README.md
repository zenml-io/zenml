# Query the metadata store inside a step function
## Overview

This example builds on the [quickstart](../quickstart) but showcases how to use a `StepContext` to query the metadata store while running a step.
We use this to evaluate all models of past training pipeline runs and store the currently best model. 
In our inference pipeline we could then easily query the metadata store the fetch the best performing model.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install sklearn

# pull example
zenml example pull step_context
cd zenml_examples/step_context

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```

## SuperQuick `step_context` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run step_context
```
