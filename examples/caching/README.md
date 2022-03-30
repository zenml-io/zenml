# Caching and its power in machine learning
A machine learning pipeline is usually made up of many steps. Each step takes some sort of input and usually produces 
some output that other steps further down the pipeline consume. As such, these pipelines describe the flow of
data through a collection of logical operations. This is where caching comes into play. We can cache the output data of
each step when we run the pipeline. If we rerun the pipeline we will only rerun an individual step if something has 
changed in the implementation of the step itself or in the upstream data. In case nothing has changed its safe to assume
our previous output data is still valid and we can just use the cached output value.

## Benefits of Caching
- **🔁 Iteration Efficiency** - When experimenting, it really pays to have a high frequency of iteration. You learn 
when and how to course correct earlier and more often. Caching brings you closer to that by making the costs of 
frequent iteration much lower.
- **💪 Increased Productivity** - The speed-up in iteration frequency will help you solve problems faster, making 
stakeholders happier and giving you a greater feeling of agency in your machine learning work.
- **🌳 Environmental Friendliness** - Caching saves you the 
[needless repeated computation steps](https://machinelearning.piyasaa.com/greening-ai-rebooting-the-environmental-harms-of-machine/) 
which mean you use up and waste less energy. It all adds up!
- **＄ Reduced Costs** - Your bottom-line will thank you! Not only do you save the planet, but your monthly cloud 
bills might be lower on account of your skipping those repeated steps.


## Overview
This example builds on the [quickstart](../quickstart) but showcases how easy ZenML leverages caching to make 
subsequent pipeline runs faster.

We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) 
digits and train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/).

The script will actually run make two pipeline runs to showcase the effect of caching on runtimes.

Depending on the chosen mode the second run will show the different caching behaviours of ZenML.

This results in the second pipeline run to be **~70 times** faster due to the power of caching.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml 

# install ZenML integrations
zenml integration install tensorflow

# pull example
zenml example pull caching
cd zenml_examples/caching
```

### Run the project
Now we're ready to run our code. There are 3 different modes explained in this example:

**Default Caching Behaviour**
Zenml uses caching by default. This means if you run the same pipeline twice, the second run will rely on the cache of 
the first run.This will run the same pipeline twice. The second run will be significantly faster as none of the steps 
are actually run and the cached output is returned.

```shell
python run.py --mode default
```

**Invalidated Cache**
Within this mode the configuration of the trainer step is changed. This changed config leads to the invalidation of the 
cached Output of the step. All steps from the trainer step onwards will be run again in the second pipeline run.

```shell
python run.py --mode invalidate
```

**Disable Caching**
Zenml allows for disabling of caching at the step level as well as the pipeline level. In this case caching has been
disabled on the normalization step. This means the normalization step as well as all steps that depend on the output
of the normalization step will be rerun on the second pipeline run.

```shell
python run.py --mode disable
```

### See results
Inspecting the logs, you would be able to see a difference in how fast the runs were. E.g.:

```shell
Step `normalizer` has started.
Step `normalizer` has finished in 2.420s.  # first run
```

```shell
Step `normalizer` has started.
Step `normalizer` has finished in 0.034s.  # second run
```

This is almost a **70x** speed increase!

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```

To see a visual representation of caching, check out the [lineage](../lineage) example. It show-cases how different 
steps in a pipeline run are cached!

## SuperQuick `caching` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run caching
```
