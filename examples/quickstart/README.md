# :running: Get up and running quickly

Build your first ML pipelines with ZenML.

## :question: Coming from `zenml go` ?
Then open [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) to get started.

## :earth_americas: Overview

This quickstart aims to give you a small illustration of what ZenML can do. To do so, we will:
- Train a model on the MNIST digits dataset, evaluate it, deploy it, and embed it in an inference pipeline
- Automatically version, track, and cache data, models, and other artifacts
- Track model hyperparameters and metrics in an experiment tracking tool
- Measure and visualize train-test skew, training-serving skew, and data drift

**New to MLOps?** You might want to start with our [**ZenBytes**](https://github.com/zenml-io/zenbytes) lesson series instead where we cover each MLOps concept in much more detail. This quickstart assumes you are already familiar with basic MLOps concepts and just want to learn how to approach them with ZenML.

## :cloud: Run on Colab
You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

### :page_facing_up: Prerequisites 
To run locally, install ZenML and pull this quickstart:

```shell
# Install ZenML
pip install zenml

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
zenml integration install dash sklearn mlflow evidently facets

# Initialize ZenML
zenml init

# Create a new ZenML profile and set it as active
zenml profile create quickstart
zenml profile set quickstart

# Register required ZenML stack
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow
zenml stack update default -d mlflow_deployer -e mlflow_tracker

# Run the quickstart script
python run.py
```

### :sponge: Clean up

To clean up, simply delete the examples folder we downloaded earlier:

```shell
rm -rf zenml_examples
```

## :bulb: Learn More

If you want to learn more about ZenML, 
then the [:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) 
are the perfect place to get started.

Already have an MLOps stack in mind?
ZenML most likely has
[**:link: Integrations**](https://docs.zenml.io/mlops-stacks/integrations) 
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