# 🧑‍💻 ZenML Examples

Here you can find a list of practical examples on how you can use ZenML
integrations with brief descriptions for each example. In case you run into
any open questions while interacting with our examples, feel free
to check our [docs](https://docs.zenml.io/).

The examples contain aspects that span across the whole range of tools and
concepts that are integral to the MLOps ecosystem.

## 🧪 Experiment Tracking

Certain phases of machine learning projects require a large amount of
experimentation with many possible approaches. Experiment tracking is vital
to capture and compare all your experiments so that you can narrow down your
solution space.

- **[mlflow_tracking](mlflow_tracking/README.md)**: Track and visualize
  experiment runs
  with [MLflow Tracking](https://mlflow.org/docs/latest/tracking.html).
- **[wandb_tracking](wandb_tracking/README.md)**: Track and visualize experiment
  runs
  with  [Wandb Experiment Tracking](https://wandb.ai/site/experiment-tracking).

## 🚅 Pipeline Orchestration

Quickly iterating is usually easiest when you code on your local machine. But
there comes a point where you will want to have your pipelines run free from
all the limitations of your local setup (performance, data access, uptime,
etc ...). With ZenML you can quickly switch out the pipeline code orchestrator
using the CLI. Here are some examples on how:

- **[airflow_orchestration](airflow_orchestration/README.md)**: Running
  pipelines with Airflow locally.
- **[kubeflow_pipelines_orchestration](kubeflow_pipelines_orchestration/README.md)**:
  Shows how to orchestrate a pipeline using a local Kubeflow stack.

## 🚀 Model Deployment

What good are your models if no-one gets to interact with them? ZenML offers you
some easy ways to quickly deploy your
model.

- **[mlflow_deployment](mlflow_deployment/README.md)**: Deploys your trained
  models to a **local** MLflow deployment service and allows you to run
  predictions against this endpoint.
- **[seldon_core_deployment](seldon_deployment/README.md)**: Take your model
  deployment to the next level with Seldon. This example gives you detailed
  instructions to help you deploy your model onto a Kubernetes cluster.

## 🥾 Step Operators

Not all steps are created equal. While some steps need only a bit of
computational power, the training step is usually a different beast altogether,
with a big appetite for CUDA cores and VRAM. This is where Step Operators
will make your life easy. With just a bit of configuration your training step
can easily be run on Vertex AI, Sagemaker or AzureML. Check out our example
to see how.

- **[step_operator_remote_training](step_operator_remote_training/README.md)**:
  Run your compute-intensive steps on one of the big three hyperscalers
  **Vertex AI**, **Sagemaker** or **AzureML**.

## 🗿 Miscellaneous Tools

Some of our integrations don't really fit into a specific category.

- **[huggingface](huggingface/README.md)**: [`Hugging Face`](https://huggingface.co/)
  is a startup in the Natural Language Processing (NLP) domain offering its
  library of SOTA models in particular around Transformers. See how you can
  get started using huggingface datasets, models and tokenizers with ZenML.
- **[neural_prophet](neural_prophet/README.md)**: NeuralProphet is a time-series
  model that bridges the gap between traditional time-series models and deep
  learning methods. Try this example to find out how this type of model
  can be trained using ZenML
- **[xgboost](xgboost/README.md)**: [XGBoost](https://xgboost.readthedocs.io/en/stable/)
  is an optimized distributed gradient boosting library that provides a
  parallel tree boosting algorithms.
- **[lightgbm](lightgbm/README.md)**: LightGBM is a gradient boosting framework
  that uses tree-based learning algorithms with a focus on distributed,
  efficient training.

## 🗂 Feature Stores

What is data-centric machine learning without data? Feature stores are the
modern approach to advanced data management layer for machine learning that
allows to share and discover features for creating more effective machine
learning pipelines.

- **[feast_feature_store](feast_feature_store/README.md)**: Use a feature store
  hosted on a local Redis server to get started with
  [Feast](https://feast.dev/).

## 📊 Data Validation

Testing your data for integrity problems and monitoring how its characteristics
evolve and drift over time are best practices that are essential not only for
developing highly accurate machine learning models, but also for keeping them
from deteriorating after they are deployed in production. Data Validators
enhance your pipelines with data quality testing and monitoring and allow you
to visualize the results in the post-execution workflow.

- **[deepchecks_data_validation](deepchecks_data_validation/README.md)**: Run
  data integrity, data drift and model drift tests in your pipelines with our
  [Deepchecks](https://github.com/deepchecks/deepchecks) integration.
- **[evidently_drift_detection](evidently_drift_detection/README.md)**: Detect
  drift with our [Evidently](https://github.com/evidentlyai/evidently)
  integration.
- **[great_expectations_data_validation](great_expectations_data_validation/README.md)**:
  Validate your data with our
  [Great Expectations](https://greatexpectations.io/) integration.
- **[whylogs_data_profiling](whylogs_data_profiling/README.md)**: Profile your
  data using the [whylogs](https://github.com/whylabs/whylogs) integration.
- **[facets_visualize_statistics](facets_visualize_statistics/README.md)**:
  The [facets](https://pair-code.github.io/facets/) integration allows you to
  retroactively go through pipeline runs and analyze the statistics of the data
  artifacts.

## 🖥 Local Setup

For some of these examples, ZenML provides a handy CLI command to pull them
directly into your local environment. First install `zenml` and spin up the
dashboard:

```shell
# Install ZenML
pip install zenml[server]

# Start the ZenServer to enable dashboard access
zenml up
```

Then you can view all the examples:

```shell
zenml example list
```

And pull individual ones:

```shell
# By doing this, a `zenml_examples` directory would be created with the examples
zenml example pull EXAMPLE_NAME
```

You can now even run the example directly with a one-liner:

```shell
zenml example run EXAMPLE_NAME  # not implemented for all examples
```

## Remote Setup on the cloud

Some of our examples feature remote stack components, or they have an emphasis
on the collaboration aspect of ZenML. In order to see this in full effect,
you might require a ZenML server.

In order to deploy a ZenML server, you can follow the instructions
[here](https://docs.zenml.io/user-guide/starter-guide/switch-to-production).

## ☎️ Talk to us

Have any questions? Want more examples? Did you spot any outdated, frustrating
examples?
We got you covered!

Feel free to let us know by creating an
[issue](https://github.com/zenml-io/zenml/issues) here on our GitHub or by
reaching out to us on our [Slack](https://zenml.io/slack-invite/).

We are also always looking for contributors. So if you want to enhance our
existing examples or add new ones, feel free
to make all Pull Request. Find out more [here](../CONTRIBUTING.md).
