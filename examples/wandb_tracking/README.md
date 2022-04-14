# Integrating Weights & Biases tracking into your pipeline

[Weights&Biases](https://wandb.ai/site/experiment-tracking) is a popular
tool that tracks and visualizes experiment runs with their many parameters,
metrics and output files.

## Overview

This example builds on the [quickstart](../quickstart) but showcases how easily
Weights & Biases (`wandb`) tracking can be integrated into a ZenML pipeline.

We'll be using the
[MNIST](http://yann.lecun.com/exdb/mnist/) dataset and
will train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/).
We will run two experiments with different parameters (epochs and learning rate)
and log these experiments into a wandb backend. 

In the example script, the [Keras WandbCallback](https://docs.wandb.ai/ref/python/integrations/keras/wandbcallback) is
used within the training step to directly hook into the TensorFlow training and
it will log out all relevant parameters, metrics and output files. Additionally,
we explicitly log the test accuracy within the evaluation step.

Note that despite `wandb `being used in different steps within a pipeline, ZenML handles initializing `wandb` 
and ensures the experiment name is the same as the pipeline name, and the experiment run is the same name 
as the pipeline run name. This establishes a lineage between pipelines in ZenML and experiments in `wandb`.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install tensorflow wandb -f

# pull example
zenml example pull wandb_tracking
cd zenml_examples/wandb_tracking

# initialize
zenml init
```

### Set up Weights&Biases
To get this example running, you need to set up a [Weights & Biases] account. You can do this for free [here](https://wandb.ai/login?signup=true).

After signing up, you will be given a username (what Weights & Biases calls an `entity`), and you can go ahead and create your first project.

Note, that in case you have a shared Weights & Biases account, the `entity` can also be your organization or team's name.


### Set up Environment Variables
There are three environment variables that are required (as of this release) to run this example.
Please note that in the upcoming releases, we will migrate the integration towards a stack component, so 
this usage will be deprecated. 

```shell
export WANDB_PROJECT_NAME=PROJECT_NAME # name of wandb project
export WANDB_ENTITY=ENTITY_NAME  # username or team name
export WANDB_API_KEY=YOUR_WANDB_ENTITY_KEY  # find this in your wandb dashboard
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
```

### See results
The results should be available at the URL: https://wandb.ai/{ENTITY_NAME}/{PROJECT_NAME}/runs/

You should see the following visualizations:

![Table Results](assets/wandb_table_results.png)

![Chart Results](assets/wandb_charts_results.png)


### Clean up
In order to clean up, delete the remaining ZenML references:

```shell
rm -rf zenml_examples
```

## SuperQuick `wandb` run

If you're really in a hurry and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run wandb_tracking
```
