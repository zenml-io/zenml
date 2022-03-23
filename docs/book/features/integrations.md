---
description: Use these tools out-of-the-box with ZenML.
---

# Integrations

**ZenML** integrates with many different third-party tools.

Once code is organized into a ZenML pipeline, you can supercharge your ML development with powerful integrations on 
multiple [MLOps stacks](../introduction/core-concepts.md). There are lots of moving parts for all the MLOps tooling 
and infrastructure you require for ML in production and ZenML aims to bring it all together under one roof.

We currently support [Airflow](https://airflow.apache.org/) and [Kubeflow](https://www.kubeflow.org/) as third-party 
orchestrators for your ML pipeline code. ZenML steps can be built from any of the other tools you usually use in your 
ML workflows, from [`scikit-learn`](https://scikit-learn.org/stable/) to [`PyTorch`](https://pytorch.org/) or 
[`TensorFlow`](https://www.tensorflow.org/).

![ZenML is the glue](../assets/zenml-is-the-glue.jpeg)

These are the third-party integrations that ZenML currently supports:

| Integration | Status | Type                   | Implementation Notes                                                                          | Example                                                                                                                                                  |
| ----------- | ------ |------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Apache Airflow | ✅ | Orchestrator           | Works for local environment.                                                                  | [airflow_local](https://github.com/zenml-io/zenml/tree/main/examples/airflow_local)                                                                      |
| Apache Beam | ✅ | Distributed Processing |                                                                                               |                                                                                                                                                          |
| AWS | ✅ | Cloud                  | Use S3 buckets as ZenML artifact stores and Sagemaker as a ZenML step operator.               | [sagemaker_step_operator](https://github.com/zenml-io/zenml/tree/main/examples/sagemaker_step_operator)                                                                                                                       |
| Azure | ✅ | Cloud                  | Use Azure Blob Storage buckets as ZenML artifact stores and AzureML as a ZenML step operator. | [azureml_step_operator](https://github.com/zenml-io/zenml/tree/main/examples/azureml_step_operator)                                                                                                                         |
| BentoML | ⛏ | Cloud                  | Looking for community implementors.                                                           |                                                                                                                                                          |
| Dash | ✅ | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | [lineage](https://github.com/zenml-io/zenml/tree/main/examples/lineage)                                                                                  |
| Evidently | ✅ | Monitoring             | Allows for visualization of drift as well as export of a `Profile` object.                    | [drift_detection](https://github.com/zenml-io/zenml/tree/release/0.5.7/examples/drift_detection)                                                         |
| Facets | ✅ | Visualizer             |                                                                                               | [statistics](https://github.com/zenml-io/zenml/tree/main/examples/statistics)                                                                            |
| GCP | ✅ | Cloud                  | Use Google Cloud Storage buckets as ZenML artifact stores.                                    |                                                                                                                                                          |
| Graphviz | ✅ | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | [dag_visualizer](https://github.com/zenml-io/zenml/tree/main/examples/dag_visualizer)                                                                    |
| Great Expectations | ⛏ | Data Validation        | Looking for community implementors.                                                           |                                                                                                                                                          |
| KServe | ⛏ | Inference              | Looking for community implementors.                                                           |                                                                                                                                                          |
| Kubeflow | ✅ | Orchestrator           | Either full Kubeflow or Kubeflow Pipelines. Works for local environments currently.           | [kubeflow](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow)                                                                                |
| MLflow Tracking | ✅ | Experiment Tracking    | Tracks your pipelines and your training runs.                                                 | [mlflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking)                                                                           |
| MLflow Deployment | ✅ | Deployment             | Deploys models with the MLflow scoring server.                                                | [mlflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment)                                                                         |
| numpy | ✅ | Exploration            |                                                                                               |                                                                                                                                                          |
| pandas | ✅ | Exploration            |                                                                                               |                                                                                                                                                          |
| Plotly | ✅ | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | [lineage](https://github.com/zenml-io/zenml/tree/main/examples/lineage)                                                                                  |
| PyTorch | ✅ | Training               |                                                                                               |                                                                                                                                                          |
| PyTorch Lightning | ✅ | Training               |                                                                                               |                                                                                                                                                          |
| scikit-learn | ✅ | Training               |                                                                                               | [caching chapter](https://docs.zenml.io/v/docs/guides/functional-api/caching)                                                                            |
| Seldon | ⛏ | Cloud                  | Looking for community implementors.                                                           |                                                                                                                                                          |
| Tensorflow | ✅ | Training, Visualizer   | Tensorboard support.                                                                          | [quickstart](https://github.com/zenml-io/zenml/tree/main/examples/quickstart). [kubeflow](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow) |
| whylogs | ✅ | Logging                | Integration fully implemented for data logging.                                               | [whylogs](https://github.com/zenml-io/zenml/tree/main/examples/whylogs)                                                                                  |

✅ means the integration is already implemented.
⛏ means we are looking to implement the integration soon.

## Help us with integrations!

There are many tools in the ML / MLOps field. We have made an initial prioritization of which tools to support with 
integrations, but we also welcome community contributions. Check our [Contributing Guide](../../../CONTRIBUTING.md) for more 
details on how best to contribute.
