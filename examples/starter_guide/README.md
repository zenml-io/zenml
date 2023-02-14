# 📜 ZenML Starter Project

What would you need to get a quick understanding of the ZenML framework and
start building your own ML pipelines? The answer is a simple project template
to cover the basics of ZenML: a collection of steps and pipelines, a stack
configuration and, to top it all off, a simple but useful CLI. This is exactly
what the ZenML starter template is all about.

This project template is a good starting point for anyone starting out with
ZenML. It showcases the following fundamental ZenML concepts in a relatable
ML context:

* Designing [ZenML pipeline steps](https://docs.zenml.io/starter-guide/pipelines#step)
in general, but also particularly useful for the following applications:
    * data ingestion, data transformation and data train/test splitting
    * model training and evaluation
* Using [step parameterization and caching](https://docs.zenml.io/starter-guide/pipelines/parameters)
to design flexible and reusable steps
* Using [custom data types for your artifacts and writing materializers for them](https://docs.zenml.io/advanced-guide/pipelines/materializers)
* Constructing and running a [ZenML pipeline](https://docs.zenml.io/starter-guide/pipelines#pipeline)
* Accessing ZenML pipeline run artifacts in [the post-execution phase](https://docs.zenml.io/starter-guide/pipelines/fetching-pipelines),after a pipeline run has concluded
* Best practices for implementing and running reproducible and reliable ML
pipelines with ZenML

In addition to that, the entire project is implemented with the [scikit-learn](https://scikit-learn.org)
library and showcases how to use ZenML with a popular ML framework. It makes
heavy use of the tabular datasets and classification models that scikit-learn
provides, but the concepts and patterns it showcases are applicable to any
other ML framework.

## 👋 Introduction

This is a basic supervised learning ML project built with the
ZenML framework and its scikit-learn integration. The project trains one or more
scikit-learn classification models to make predictions on one of the tabular
classification datasets provided by the scikit-learn library. The project was
generated from the [starter ZenML project template](https://github.com/zenml-io/zenml-project-templates/tree/main/starter)

What to do first? You can start by giving the the project a quick run. The
project is ready to be used and can run as-is without any further code
changes! You can try it right away by installing ZenML, the scikit-learn
ZenML integration and then calling the CLI included in the project. We also
recommend that you start the ZenML UI locally to get a better sense of what
is going on under the hood:

```bash
# Set up a Python virtual environment, if you haven't already
virtualenv .venv
source .venv/bin/activate
# Install requirements
pip install -r requirements.txt
# Start the ZenML UI locally (recommended, but optional);
# the default username is "admin" with an empty password
zenml up
# Run the pipeline included in the project
python run.py
```

When the pipeline is done running, you can check out the results in the ZenML
UI by following the link printed in the terminal (or you can go straight to
the [ZenML UI pipelines run page](http://127.0.0.1:8237/projects/default/all-runs?page=1).

Next, you should:

* look at the CLI help to see what you can do with the project:
```bash
python run.py --help
```
* go back and [try out different parameters](https://github.com/zenml-io/zenml-project-templates/tree/main/starter#-template-parameters)
for your generated project. For example, you could enable generating step
parameters or custom materializers for your project, if you haven't already. 
* take a look at [the project structure](#📜-project-structure) and the code
itself. The code is heavily commented and should be easy to follow.
* read the [ZenML documentation](https://docs.zenml.io) to learn more about
various ZenML concepts referenced in the code and to get a better sense of
what you can do with ZenML.
* start building your own ZenML project by modifying this code

## 📦 What's in the box?

The project showcases a basic ZenML model
training pipeline with all the usual components you would expect to find in
a simple machine learning project such as this one:

- a data ingestion step that loads one of the datasets provided through
scikit-learn
- a data processing step that does some basic preprocessing (drops rows with
missing values, normalizes the data)
- a data splitting step that breaks the data into train and test sets
- a training step that trains one of the scikit-learn models on the train set
- a model evaluation step that evaluates the trained model on the train and test
sets and warns or fails the pipeline if the model performance is below a
certain threshold

The project code is meant to be used as a template for your own projects. For
this reason, you will find a number of places in the code specifically marked
to indicate where you can add your own code:

```python
### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
...
### YOUR CODE ENDS HERE ###
```

## 📜 Project Structure

The project loosely follows [the recommended ZenML project structure](https://docs.zenml.io/guidelines/best-practices#recommended-repository-structure):

```
├── pipelines                   <- All pipelines in one place
│   ├── model_training.py       <- The main (training) pipeline
├── steps                       <- All steps in one place
│   ├── data_loaders.py         <- Data loader/processor/splitter steps
│   ├── model_trainers.py       <- Model trainer/evaluator steps
├── .dockerignore 
├── README.md                   <- This file
├── requirements.txt            <- Python dependencies  
└── run.py                      <- CLI entrypoint
```