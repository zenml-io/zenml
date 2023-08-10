# :running: Get up and running quickly

Build your first ML pipelines with ZenML.

## :question: Coming from `zenml go` ?
Then open [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) to get 
started.

## :earth_americas: Overview

This quickstart demonstrates some of ZenML's features. We will:

- Import some data from a public dataset (Adult Census Income), then train two models (SGD and Random Forest)
- Compare and evaluate which model performs better, and deploy the best one.
- Run a prediction on the deployed model.

Along the way we will also show you how to:

- Automatically version, track, and cache data, models, and other artifacts,
- Track model hyperparameters and metrics in an experiment tracking tool

## :cloud: Run on Colab
You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

To run locally, install ZenML and pull this quickstart:

```shell
# Install ZenML
pip install "zenml[server]"

# clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/examples/quickstart
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
zenml integration install sklearn mlflow -y

# Initialize ZenML
zenml init

# Start the ZenServer to enable dashboard access
zenml up

# Register required ZenML stack
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow
zenml model-registry register mlflow_registry --flavor=mlflow

# Register a new stack with the new stack components
zenml stack register quickstart_stack -a default\
                                      -o default\
                                      -d mlflow_deployer\
                                      -e mlflow_tracker\
                                      -r mlflow_registry\
                                      --set

# Run the quickstart script
python run.py
```

## :dart: Dashboard

You can also take a look at our **dashboard** where you can inspect the quickstart 
pipeline run and much more. Simply execute:

```shell
# only once you've already run `zenml up`
zenml show
```

## :sponge: Clean up

To clean up, simply spin down the ZenML server.

```shell
zenml down
```

## :bulb: Learn More

If you want to learn more about ZenML as a tool, then the 
[:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) are the perfect place 
to get started.

Already have an MLOps stack in mind? ZenML most likely has
[**:link: Integrations**](https://docs.zenml.io/stacks-and-components/component-guide) 
for whatever tools you plan to use.

Also, make sure to join our <a href="https://zenml.io/slack-invite" target="_blank">
    <img width="15" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!


