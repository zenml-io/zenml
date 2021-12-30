# Utilize standard interfaces to your advantage

This examples uses a collection of built-in and integrated standard interfaces to showcase their effect
on the overall smoothness of the user experience.

We will be using the [Pima Indians Diabetes Database](https://www.kaggle.com/uciml/pima-indians-diabetes-database?select=diabetes.csv) 
and try to train a binary classifier using [Tensorflow (Keras)](https://www.tensorflow.org/) and [scikit-learn](https://scikit-learn.org/).

## Overview

In the `run.py`, we will be using a built-in pipeline called `TrainingPipeline` which requires the following steps 
to be specified:

- `datasource`: for the data ingestion 
- `splitter`: for splitting the dataset into train, test and validation datasets
- `analyzer`: for extraction the statistics and the schema of the train dataset
- `preprocesser`: for preprocessing the splits
- `trainer`: for training a model 
- `evaluator`: for the evaluation of the trained model

All of these steps need to conform to the standards set by their respective interface in `zenml.steps.step_interfaces`. 
For instance, any split step to be used within this pipeline needs to have a single input data artifact for the dataset 
and three output data artifacts for the train, test and validation splits. 

In order to get a quick start on our pipeline, we will simply be using some built-in and integrated steps such 
as `SklearnSplitter` and `TensorflowBinaryClassifier`.

## Run it locally

### Pre-requisites
In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install tensorflow
zenml integration install sklearn

# pull example
zenml example pull standard_interfaces
cd zenml_examples/standard_interfaces

# initialize
zenml init
```

### Run the project
Now we're ready. Execute:

```bash
python run.py
```

### Clean up
In order to clean up, delete the remaining zenml references.

```shell
rm -rf zenml_examples
```