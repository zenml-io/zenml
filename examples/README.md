# 🧑‍💻 ZenML Examples

Here you can find a list of practical examples on how you can use ZenML integrations with
brief descriptions for each example. In case you run into any open questions while interacting with our docs, feel free 
to check our [docs](https://docs.zenml.io/).

## 📑 Table of Contents

The examples contain aspects that span across the whole range of

### ⛲ Data Sources
No data, no fun. 

- **feast_feature_store**: 🔜 Coming very soon!

### 📊 Data Visualizers
Within ZenML, Visualizers are Python classes that take post-execution view objects (e.g. `PipelineView`, 
`PipelineRunView`, `StepView`, etc.) and create visualizations for them. 

- **[facets_visualize_statistics](facets_visualize_statistics/README.md)**: 
The [facets](https://pair-code.github.io/facets/) integration allows you to retroactively go through pipeline runs and 
analyze the statistics of the data artifacts.
- **[whylogs_data_profiling](whylogs_data_profiling/README.md)**: Profile your data using the 
[whylogs](https://github.com/whylabs/whylogs) integration from within the post-execution workflow.
- **[evidently_drift_detection](evidently_drift_detection/README.md)**: Detect drift with our 
[evidently](https://github.com/evidentlyai/evidently) integration. 

### 🗂 Experiment Tracking
Certain phases of machine learning projects require a large amount of experimentation with many possible approaches. 
Experiment tracking is vital to capture and compare all your experiments so that you can narrow down your solution 
space.

- **[mlflow_tracking](mlflow_tracking/README.md)**: Track and visualize experiment runs with 
[MLflow Tracking](https://mlflow.org/docs/latest/tracking.html). 

### 🚀 Model Deployment
What good are your models if noone gets to interact with them. ZenML offers you some easy ways to quickly deploy your 
model.

- **[mlflow_deployment](mlflow_deployment/README.md)**: Deploys your trained models to a local mlflow deployment service 
and allows you to run predictions against this endpoint.
- **seldon_core_deployment**: 🔜 Coming very soon!
- **kserve_deployment**: 🔜 Coming very soon!

### 🚅 Pipeline Orchestration
Quickly iterating on code changes is usually easiest when you code on your local machines. But there comes a point where
you will want to have your pipelines run free from all the limitations of your local setup (performance, data access,
uptime, etc ...). With zenml you can quickly switch out the pipeline code orchestrator using the CLI. Here are some 
examples on how:

- **[airflow_orchestration](airflow_orchestration/README.md)**: Running pipelines with airflow locally.
- **[kubeflow_pipeline_orchestration](kubeflow_pipeline_orchestration/README.md)**: Shows how to orchestrate a pipeline
using a local kubeflow stack.

### 🥾 Step Operators
Not all steps are created equal. While some steps need only a bit of computational power, the training step is usually 
a different beast altogether, with a big appetite for Cuda Cores and VRAM. This is where Step Operators will make your 
life easy. With just a bit of configuration your training step can easily be run on Vertex AI, Sagemaker or AzureML. 
Check out our example to see how.

- **[step_operator_remote_training](step_operator_remote_training/README.md)**: Run your compute intensive steps on one 
of the big three hyperscalers.


## 🖥 Local Setup
For each of these examples, ZenML provides a handy CLI command to pull them
directly into your local environment. First install `zenml`:

```shell
pip install zenml
```

Then you can view all the examples:

```shell
zenml example list
```

And pull individual ones:

```shell
zenml example pull EXAMPLE_NAME
# at this point a `zenml_examples` dir would be created with the examples
```

You can now even run the example directly with a one-liner:

```shell
zenml example run EXAMPLE_NAME  # not implemented for all examples
```

## ☎️ Talk to us
Have any questions? Want more examples? Did you spot any out-dated, frustrating examples?
We got you covered!

Feel free to let us know by creating an
[issue](https://github.com/zenml-io/zenml/issues) here on our GitHub or by
reaching out to us on our [Slack](https://zenml.io/slack-invite/). 