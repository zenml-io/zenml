# :running: Get up and running quickly

Build your first ML pipelines with ZenML.

## :question: Coming from `zenml go` ?
Then open [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) to get started.

## :earth_americas: Overview

This quickstart aims to give you a small illustration of what ZenML can do. To do so, we will:
- Train a model on the iris flower classification dataset, evaluate it, deploy it, and embed it in an inference pipeline,
- Automatically version, track, and cache data, models, and other artifacts,
- Track model hyperparameters and metrics in an experiment tracking tool,
- Measure and visualize train-test skew, training-serving skew, and data drift.

**New to MLOps?** You might want to start with our [**ZenBytes**](https://github.com/zenml-io/zenbytes) lesson series instead where we cover each MLOps concept in much more detail. This quickstart assumes you are already familiar with basic MLOps concepts and just want to learn how to approach them with ZenML.

## :cloud: Run on Colab
You can use Google Colab to see ZenML in action, no signup / installation required!

<a href="https://colab.research.google.com/github/zenml-io/zenml/blob/main/examples/quickstart/notebooks/quickstart.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

## :cloud: The Zen 🧘 way to run on a cloud provider of your choice

If you're looking for a quick way to test the quickstart out on your cloud but don't want to go through the pain-staking process of creating all the required resources, we have just the solution for you: [stack recipes!](../../docs/book/stack-deployment-guide/stack-recipes.md) 🥗

A flow to get started for this example can be the following:

1. 📃 List all available stack recipes.

    ```shell
    zenml stack recipe list
    ```
2. Pull the recipe that you wish to deploy, to your local system.

    ```shell
    zenml stack recipe pull <STACK-RECIPE-NAME>

3. (Optional) 🎨 Customize your deployment by editing the default values in the `locals.tf` file.

3. 🚀 Deploy the recipe with this simple command.

    ```shell
    zenml stack recipe deploy <STACK-RECIPE-NAME>
    ```
    > **Note**
    > This command can also automatically import the resources created as a ZenML stack for you. Just run it with the `--import` flag and optionally provide a `--stack-name` and you're set! Keep in mind, in that case, you'll need all integrations for this example installed before you run this command.

    > **Note**
    > You should also have [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) and [docker](https://docs.docker.com/engine/install/) installed on your local system with the local [docker client authorized](https://cloud.google.com/sdk/gcloud/reference/auth/configure-docker) to push to your cloud registry.
    
4. You'll notice that a ZenML stack configuration file gets created 🤯! You can run the following command to import the resources as a ZenML stack, manually.

    ```shell
    zenml stack import <STACK_NAME> -f <PATH_TO_THE_CREATED_STACK_CONFIG_YAML>

    # set the imported stack as the active stack
    zenml stack set <STACK_NAME>
    ```

5. You should now create secrets for your newly-created MySQL instance. If you're using a GCP recipe, you can refer to the [Kubeflow example README](../kubeflow_pipelines_orchestration/README.md#🚅-that-seems-like-a-lot-of-infrastructure-work-is-there-a-zen-🧘-way-to-run-this-example) for the necessary commands. For AWS, check out the [Kubernetes Orchestrator example README.](../kubernetes_orchestration/README.md#🚅-that-seems-like-a-lot-of-infrastructure-work-is-there-a-zen-🧘-way-to-run-this-example)


You can now run the quickstart pipeline by executing the `run.py` file in the root directory!

```bash
python run.py
```


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
zenml data-validator register evidently_data_validator --flavor=evidently
zenml experiment-tracker register mlflow_tracker --flavor=mlflow
zenml model-deployer register mlflow_deployer --flavor=mlflow
zenml stack update default -d mlflow_deployer -e mlflow_tracker -dv evidently_data_validator

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