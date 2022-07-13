---
description: Use these tools out-of-the-box with ZenML.
---

# Integrations

ZenML integrates with many different third-party tools. Once code is organized
into a ZenML pipeline, you can supercharge your ML workflows with the
best-in-class solutions from various MLOps areas.

There are lots of moving parts for all the MLOps tooling and infrastructure you
require for ML in production and ZenML brings them all together and enables you
to manage them in one place.

For example, we currently support [Airflow](https://airflow.apache.org/) and
[Kubeflow](https://www.kubeflow.org/) as third-party orchestrators for your ML
pipeline code. Experiment trackers
like [MLflow Tracking](https://www.mlflow.org/docs/latest/tracking.html) and
[Weights & Biases](https://wandb.ai/site) can be added to your ZenML
pipeline. And you can seamlessly
transition from a
local [MLflow deployment](https://www.mlflow.org/docs/latest/python_api/mlflow.deployments.html)
to
a deployed model on Kubernetes using [Seldon Core](https://www.seldon.io/).

All of this allows you to write your code now and add the right tool for the job
as soon as the need arises.

![ZenML is the glue](../assets/zenml-is-the-glue.jpeg)

These are the third-party integrations that ZenML currently supports:

| Integration               | Status | Type                   | Implementation Notes                                                                          | Example                                                                                                                                                  |
|---------------------------|--------|------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Apache Airflow            | ✅      | Orchestrator           | Works for local environment.                                                                  | [airflow_orchestration](https://github.com/zenml-io/zenml/tree/main/examples/airflow_orchestration)                                                                      |
| Apache Beam               | ✅      | Distributed Processing |                                                                                               |                                                                                                                                                          |
| AWS                       | ✅      | Container Registry     | Use the AWS container registry to store your containers.                                      |                                                                                                                                                          |
| AWS                       | ✅      | Secrets Manager        | Use AWS as a secrets manager.                                                                 | [cloud_secrets_manager](https://github.com/zenml-io/zenml/tree/develop/examples/cloud_secrets_manager)                                                   |
| AWS                       | ✅      | Step Operator          | Sagemaker as a ZenML step operator.                                                           | [sagemaker_step_operator](https://github.com/zenml-io/zenml/tree/main/examples/step_operator_remote_training)                                            |
| Azure                     | ✅      | Artifact Store         | Use Azure Blob Storage buckets as ZenML artifact stores. |                                                                                                                                                          |
| Azure                     | ✅      | Step Operator          | Use AzureML as a step operator to supercharge specific steps.                                 | [azureml_step_operator](https://github.com/zenml-io/zenml/tree/main/examples/step_operator_remote_training)                                              |
| BentoML                   | ⛏      | Deployment             | Looking for community implementors.                                                           |                                                                                                                                                          |
| Dash                      | ✅      | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | |
| Evidently                 | ✅      | Monitoring             | Allows for visualization of drift as well as export of a `Profile` object.                    | [drift_detection](https://github.com/zenml-io/zenml/tree/release/0.5.7/examples/drift_detection)                                                         |
| Facets                    | ✅      | Visualizer             | Quickly visualize your datasets using `facets`.                                               | [facets_visualize_statistics](https://github.com/zenml-io/zenml/tree/main/examples/facets_visualize_statistics)                                                                            |
| Feast                     | ✅      | Feature Store          | Use Feast with Redis for your online features.                                                | [feast_feature_store](https://github.com/zenml-io/zenml/tree/main/examples/feast_feature_store)                                                                      |
| GitHub                    | ✅      | Orchestrator           | Use GitHub Actions to orchestrate your ZenML pipelines.                                             | [github_actions_orchestration](https://github.com/zenml-io/zenml/tree/main/examples/github_actions_orchestration) |
| GCP                       | ✅      | Artifact Store         | Use GCS buckets as a ZenML artifact store.                                                    |                                                                                                                                                          |
| GCP                       | ✅      | Step Secrets Manager   | Use the GCP Secret Manager.                                                                   | [cloud_secrets_manager](https://github.com/zenml-io/zenml/tree/develop/examples/cloud_secrets_manager)                                                   |
| GCP                       | ✅      | Step Operator          | Vertex AI as a ZenML step operator.                                                           | [vertex_step_operator](https://github.com/zenml-io/zenml/tree/main/examples/step_operator_remote_training)                                               |
| GCP                       | ✅      | Orchestrator           | Execute your ZenML pipelines using Vertex AI Pipelines.                                        |                                                                                                                                                          |
| Graphviz                  | ✅      | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | |
| Great Expectations        | ⛏      | Data Validation        | Looking for community implementors.                                                           |                                                                                                                                                          |
| Hugging Face              | ✅      | Materializer           | Use Hugging Face tokenizers, datasets and models.                                             | [huggingface](https://github.com/zenml-io/zenml/tree/main/examples/huggingface)                                                                          |
| KServe                    | ⛏      | Inference              | Looking for community implementors.                                                           |                                                                                                                                                          |
| Kubeflow                  | ✅      | Orchestrator           | Either full Kubeflow or Kubeflow Pipelines. Works for local environments currently.           | [kubeflow_pipelines_orchestration](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration)                                                                                |
| Kubernetes                  | ✅      | Orchestrator           | Only works with remote clusters currently. | [kubernetes_orchestration](https://github.com/zenml-io/zenml/tree/main/examples/kubernetes_orchestration)                                                                                |
| lightgbm                  | ✅      | Training               | Support for `Booster` and `Dataset` materialization.                                          | [lightgbm](https://github.com/zenml-io/zenml/tree/main/examples/lightgbm)                                                                                |
| MLflow Tracking           | ✅      | Experiment Tracking    | Tracks your pipelines and your training runs.                                                 | [mlflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_tracking)                                                                           |
| MLflow Deployment         | ✅      | Deployment             | Deploys models with the MLflow scoring server.                                                | [mlflow](https://github.com/zenml-io/zenml/tree/main/examples/mlflow_deployment)                                                                         |
| NeuralProphet             | ✅      | Training               | Enables materializing NeuralProphet models.                                                   | [neural_prophet](https://github.com/zenml-io/zenml/tree/main/examples/neural_prophet)                                                                    |
| numpy                     | ✅      | Exploration            |                                                                                               |                                                                                                                                                          |
| pandas                    | ✅      | Exploration            |                                                                                               |                                                                                                                                                          |
| Plotly                    | ✅      | Visualizer             | For Pipeline and PipelineRun visualization objects.                                           | |
| PyTorch                   | ✅      | Training               |                                                                                               | [pytorch](https://github.com/zenml-io/zenml/tree/main/examples/pytorch)                                                                                  |
| PyTorch Lightning         | ✅      | Training               |                                                                                               |                                                                                                                                                          |
| S3                        | ✅      | Artifact Store         | Use S3 buckets as ZenML artifact stores.                                                      | |
| scikit-learn              | ✅      | Training               |                                                                                               | |
| scipy                     | ✅      | Materializer           | Use sparse matrices.                                                                          |                                                                                                                                                          |
| Seldon Core               | ✅      | Deployment             | Seldon Core as a model deployer.                                                              | [seldon_deployment](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment)                                                                         |
| Slack               | ✅      | Alerter             | Send automated alerts to Slack.                                                              | [slack_alert](https://github.com/zenml-io/zenml/tree/main/examples/slack_alert)  
| Tensorflow                | ✅      | Training, Visualizer   | TensorBoard support.                                                                          | [kubeflow_pipelines_orchestration](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration) |
| Weights & Biases | ✅      | Experiment Tracking    | Tracks your pipelines and your training runs.                                                 | [wandb_tracking](https://github.com/zenml-io/zenml/tree/main/examples/wandb_tracking)                                                                    |
| whylogs                   | ✅      | Logging                | Integration fully implemented for data logging.                                               | [whylogs_data_profiling](https://github.com/zenml-io/zenml/tree/main/examples/whylogs_data_profiling)                                                                                  |
| xgboost                   | ✅      | Training               | Support for `Booster` and `DMatrix` materialization.                                          | [xgboost](https://github.com/zenml-io/zenml/tree/main/examples/xgboost)                                                                                  |
| Vault                   | ✅      | Secrets Manager               | Use Vault Key/Value Secrets Engine                                        |                                                                                   |

✅ means the integration is already implemented.
⛏ means we are looking to implement the integration soon.

## Help us with integrations!

There are many tools in the ML / MLOps field. We have made an initial
prioritization of which tools to support with integrations, but we also welcome
community contributions. Check our
[Contributing Guide](../../../CONTRIBUTING.md) for more details on how best to
contribute.
