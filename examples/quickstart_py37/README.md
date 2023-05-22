# :running: Get up and running quickly

Build your first ML pipelines with ZenML.

## :question: Coming from `zenml go` ?
Then open [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) to get 
started.

## :earth_americas: Overview

This quickstart aims to give you a small illustration of what ZenML can do. 
In order to achieve that, we will:
- Train a model on the iris flower classification dataset, evaluate it, deploy 
it, and embed it in an inference pipeline,
- Automatically version, track, and cache data, models, and other artifacts,
- Track model hyperparameters and metrics in an experiment tracking tool,
- Measure and visualize train-test skew, training-serving skew, and data drift.

{% hint style="warning" %}
Please note that this version of the `quickstart` is intended for use with
Python 3.7 and does not support the [MLflow model registry](https://docs.zenml.io/component-gallery/model-registries/mlflow).
If you are using Python 3.8 or higher, we recommend that you use the quickstart
instead. The main difference between the two versions is that this version
deploys the model directly to MLflow after training, whereas the other version
registers the model with the MLflow model registry, then deploys a given version
of the model.
{% endhint %}

## :star: Introduction to ZenML

Before we dive into the code, let us briefly introduce you to some 
fundamental concepts of ZenML that we will use in this quickstart. If you are 
already familiar with these concepts, feel free to skip to the next section.

#### Steps

The first concept that we will cover in this section is the ZenML **Step**. In 
ZenML, a step provides a simple python interface to our users to design a 
stand-alone process in an ML workflow. They consume input artifacts 
and generate output artifacts. As an example, we can take a closer look at one 
of the steps in the pipeline above:

```python
import pandas as pd

from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

from zenml import step
from zenml.steps import Output

@step
def training_data_loader() -> Output(
    X_train=pd.DataFrame,
    X_test=pd.DataFrame,
    y_train=pd.Series,
    y_test=pd.Series,
):
    """Load the iris dataset as tuple of Pandas DataFrame / Series."""
    iris = load_iris(as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, shuffle=True, random_state=42
    )
    return X_train, X_test, y_train, y_test
```

#### Pipelines

Following the steps, you will go over the concepts of **Pipelines**. These 
pipelines provide our users a simple python interface to design their ML 
workflows by linking different steps together. For instance, the training 
pipeline that we will use in this example looks like this:

```python
from zenml import pipeline

@pipeline(enable_cache=False)
def training_pipeline(
    training_data_loader,
    trainer,
    evaluator,
    deployment_trigger,
    model_deployer,
):
    """Train, evaluate, and deploy a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(test_acc)
    model_deployer(deployment_decision, model)
```

#### Stacks & Stack Components

As for the execution of these pipelines, you need a **stack**. In ZenML, 
a stack stands for a set of configurations of your MLOps tools and 
infrastructure. Each stack consists of multiple **stack components** and
depending on their type, these components serve different purposes.

If you look at some examples of different flavors of stack components, you 
will see examples such as:

- [Airflow**Orchestrator**]() which orchestrates your ML workflows on Airflow
- [MLflow**ExperimentTracker**]() which can track your experiments with MLFlow
- [Evidently**DataValidator**]() which can help you validate your data

Any such combination of tools and infrastructure can be registered as a 
separate stack in ZenML. Since ZenML code is tooling-independent, you can 
switch between stacks with a single command and then automatically execute your
ML workflows on the desired stack without having to modify your code.

#### Integrations

Finally, ZenML comes equipped with a wide variety of stack components flavors. 
While some of these flavors come built-in with the ZenML package, the others 
are implemented as a part of one of our integrations. Since our quickstart 
features some of these integrations, you will see a practical example on how 
to use these integrations in the upcoming sections.

## :cloud: Run on Colab
You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

### :page_facing_up: Prerequisites 
To run locally, install ZenML and pull this quickstart:

```shell
# Install ZenML
pip install "zenml[server]"

# Pull this quickstart to zenml_examples/quickstart
zenml example pull quickstart
cd zenml_examples/quickstart
```

### :arrow_forward: Run Locally
Now we're ready to start. You have two options for running the quickstart locally:

#### Option 1 (*Recommended*) - Interactively explore the quickstart using Jupyter Notebook:
```bash
pip install notebook
jupyter notebook
# open notebooks/quickstart.ipynb
```

#### Option 2 - Execute the whole ML pipeline from a Python script:
```bash
# Install required zenml integrations
zenml integration install sklearn mlflow evidently -y

# Initialize ZenML
zenml init

# Start the ZenServer to enable dashboard access
zenml up

# Register required ZenML stack
zenml data-validator register evidently_data_validator --flavor=evidently
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow

# Register a new stack with the new stack components
zenml stack register quickstart_py37_stack -a default\
                                      -o default\
                                      -d mlflow_deployer\
                                      -e mlflow_tracker\
                                      -dv evidently_data_validator\
                                      --set

# Run the quickstart script
python run.py
```

## :dart: Dashboard

In addition to the visualization generated by the Evidently data validator, you 
can also take a look at our **dashboard** where you can inspect the quickstart 
pipeline run and much more. Simply execute:

```shell
zenml up
```

## :sponge: Clean up

To clean up, simply spin down the ZenML server and delete the examples folder 
we downloaded earlier:

```shell
zenml down

rm -rf zenml_examples
```

## :bulb: Learn More

If you want to learn more about ZenML as a tool, then the 
[:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) are the perfect place 
to get started.

If you are new to MLOps, you might want to take a look at our 
[**ZenBytes**](https://github.com/zenml-io/zenbytes) lesson series instead 
where we cover each MLOps concept in much more detail.

Already have an MLOps stack in mind? ZenML most likely has
[**:link: Integrations**](https://docs.zenml.io/component-gallery/integrations) 
for whatever tools you plan to use. Check out the
[**:pray: ZenML Examples**](https://github.com/zenml-io/zenml/tree/main/examples)
to see how to use a specific tool with ZenML.

If you would like to learn more about the various MLOps concepts, check out
[**:teacher: ZenBytes**](https://github.com/zenml-io/zenbytes),
our series of short practical MLOps lessons.

Also, make sure to join our <a href="https://zenml.io/slack-invite" target="_blank">
    <img width="15" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!


