# :running: MLOps 101 with ZenML

Build your first MLOps pipelines with ZenML.

## :earth_americas: Overview

This repository is a minimalistic MLOps project intended as a starting point to learn how to put ML workflows in production. 

This is a representation of how it will all come together: 

<img src=".assets/pipeline_overview.png" width="70%" alt="Pipelines Overview">

Along the way we will also show you how to:

- Structure your code into MLOps pipelines.
- Transition your ML models from local development environment to your cloud infrastructure.

## 🏃 Run on Colab

You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :computer: Run Locally

To run locally, install ZenML and pull this quickstart:

```shell
# Install ZenML
pip install "zenml[server]"

# clone the ZenML repository
git clone https://github.com/zenml-io/zenml.git
cd zenml/examples/quickstart
```

Now we're ready to start. You have two options for running the quickstart locally:

#### Option 1 - Interactively explore the quickstart using Jupyter Notebook:
```bash
pip install notebook
jupyter notebook
# open notebooks/quickstart.ipynb
```

#### Option 2 - Execute the whole training pipeline from a Python script:

```bash
# Install required zenml integrations
zenml integration install sklearn -y

# Initialize ZenML
zenml init

# Start the ZenServer to enable dashboard access
zenml connect --url=""

# Run the pipeline locally
python run.py --model_type=t5-small --orchestration_environment local
```

## 🌵 Running Remotely

```
zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-large --orchestration_environment aws
```
```
zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-large --orchestration_environment gcp
```

```
zenml stack set <INSERT_YOUR_STACK_NAME_HERE>
python run.py --model_type=t5-large --orchestration_environment azure
```




## :bulb: Learn More

You're a legit MLOps engineer now! You trained two models, evaluated them against
a test set, registered the best one with the ZenML model control plane,
and served some predictions. You also learned how to iterate on your models and
data by using some of the ZenML utility abstractions. You saw how to view your
artifacts and stacks via the client as well as the ZenML Dashboard.

If you want to learn more about ZenML as a tool, then the
[:page_facing_up: **ZenML Docs**](https://docs.zenml.io/) are the perfect place
to get started. In particular, the [Production Guide](https://docs.zenml.io/user-guide/production-guide/)
goes into more detail as to how to transition these same pipelines into production on the cloud.

The best way to get a production ZenML instance up and running with all batteries included is the [ZenML Pro](https://zenml.io/pro). Check it out!

Also, make sure to join our <a href="https://zenml.io/slack" target="_blank">
    <img width="15" src="https://cdn3.iconfinder.com/data/icons/logos-and-brands-adobe/512/306_Slack-512.png" alt="Slack"/>
    <b>Slack Community</b> 
</a> to become part of the ZenML family!
