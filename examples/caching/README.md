# Caching and its power in machine learning
If we organise the steps of our model training smartly, we can ensure that the data outputs and inputs along the way are cached. A good way to think about splitting up the steps is to use the image of [pipelines](https://blog.zenml.io/tag/pipelines/) and the steps that are executed. 
For each step, data is passed in, and (potentially) gets returned. We can cache the data at these entry and exit points. If we rerun the pipeline we will only rerun an individual step if something has changed in the implementation, otherwise we can just use the cached output value.

## Benefits of Caching
- **🔁 Iteration Efficiency** - When experimenting, it really pays to have a high frequency of iteration. You learn when and how to course correct earlier and more often. Caching brings you closer to that by making the costs of frequent iteration much lower.
- **💪 Increased Productivity** - The speed-up in iteration frequency will help you solve problems faster, making stakeholders happier and giving you a greater feeling of agency in your machine learning work.
- **🌳 Environmental Friendliness** - Caching saves you the [needless repeated computation steps](https://machinelearning.piyasaa.com/greening-ai-rebooting-the-environmental-harms-of-machine/) which mean you use up and waste less energy. It all adds up!
- **＄ Reduced Costs** - Your bottom-line will thank you! Not only do you save the planet, but your monthly cloud bills might be lower on account of your skipping those repeated steps.


## Overview
This example builds on the [quickstart](../quickstart) but showcases how easy ZenML leverages caching to make subsequent pipeline runs faster.

We'll be using the [MNIST](http://yann.lecun.com/exdb/mnist/) dataset (originally developed by Yann LeCun and others) digits and train a classifier using [Tensorflow (Keras)](https://www.tensorflow.org/).

The script will actually run make two pipeline runs, with different configurations of the trainer. In the second run, the first two steps will be skipped (i.e. the importing the data and preprocessing it)

This results in the second pipeline run to be **~70 times** faster due to the power of caching.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml tensorflow

# pull example
zenml example pull caching
cd zenml_examples/caching

# initialize
git init
zenml init
```

### Run the project
Now we're ready. Execute:

```shell
python run.py
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

To see a visual representation of caching, check out the [lineage](../lineage) example. It show-cases how different steps in a pipeline run are cached!