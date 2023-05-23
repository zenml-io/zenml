---
description: Individually deploying different stack components.
---

# Deploy a stack component

TODO: This page requires more details about the general flow of deploying components and focus on a use case story and 
try to talk about each stage along the journey for more advanced users.

You can deploy individual stack components using the `zenml <STACK_COMPONENT> deploy` CLI 🚀. For example, to deploy an MLflow tracking server on a GCP account, you can run:

{% code overflow="wrap" %}
```bash
zenml experiment-tracker deploy my_tracker --flavor=mlflow --cloud=gcp --project_id="zenml"
```
{% endcode %}

The command above takes in the following parameters:

* **Name**: The name of the stack component. In this case, it is `my_tracker` . If you don't provide a name, a random one is generated for you.
* **Flavor:** What flavor of the stack component to deploy. Here, we are deploying an MLflow experiment tracker.
* **Cloud:** What cloud to deploy this stack component on. Currently, only **GCP, AWS, and k3d** are supported as providers).
* **Additional Configuration:** Some components can be customized by the user and these settings are passed as flags to the command. In the example above, we pass the GCP project ID to select what project to deploy the component to.

A successful execution of this command also registers the deployed stack component with your ZenML server, so you don't have to worry about manually configuring components after the deployment! 🤩

{% hint style="info" %}
The command currently uses your local credentials for GCP and AWS to provision resources. Integration with your ZenML connectors might be possible soon too!
{% endhint %}

### 🍨 Available flavors for stack components

Here's a table of all the flavors that can be deployed through the CLI for every stack component. This is a list that will keep on growing and you can also contribute any flavor or stack component that you feel is missing. Refer to the [Contribution page](contributing-flavors-or-components.md) for steps on how to do that :smile:

| Component Type     | Flavor       |
| ------------------ | ------------ |
| Experiment Tracker | mlflow       |
| Model Deployer     | seldon       |
|                    | kserve       |
| Artifact Store     | s3           |
|                    | gcs          |
|                    | minio        |
| Orchestrator       | kubernetes   |
|                    | kubeflow     |
|                    | tekton       |
|                    | sagemaker    |
| Step Operator      | sagemaker    |
|                    | vertex       |
| Container Registry | gcr          |
|                    | ecr          |
|                    | k3d-registry |

### ✨ Customizing your stack components

You can pass configuration specific to the stack components as key-value arguments to the deploy CLI. Here are all possible configurations that can be set.

**Experiment Trackers**

You can assign an existing bucket to the MLflow experiment tracker by using the `--mlflow_bucket` flag:

```shell
zenml experiment-tracker deploy mlflow_tracker --flavor=mlflow --mlflow_bucket=gs://my_bucket
```

**Artifact Stores**

For an artifact store, you can pass `bucket_name` as an argument to the command.

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --bucket_name=my_bucket
```

**Container Registries**

For container registries you can pass the repository name using `repo_name`:

```bash
zenml container-registry deploy aws_registry --flavor=aws --repo_name=my_repo
```

This is only useful for the AWS case since AWS requires a repository to be created before pushing images to it and the deploy command ensures that a repository with the name you provide is created. In case of GCP and other providers, you can choose the repository name at the same time as you are pushing the image via code. This is achieved through setting the `target_repo` attribute of the [the `DockerSettings` object](broken-reference).

#### Other configuration

* You can also pass a region to deploy your resources to in the case of AWS and GCP recipes. For example, to deploy an S3 artifact store in the `us-west-2` region, you can run:

<pre class="language-bash"><code class="lang-bash"><strong>zenml artifact-store deploy s3_artifact_store --flavor=s3 --region=us-west-2
</strong></code></pre>

The default region is `eu-west-1` for AWS and `europe-west1` for GCP.

{% hint style="warning" %}
Changing regions is not recommended as it can lead to unexpected results for components that share infrastructure like Kubernetes clusters. If you must do so, please destroy all the stack components from the older region by running the `destroy` command and then redeploy using the `deploy` command.
{% endhint %}

* In the case of GCP components, it is _required_ that you pass a project ID to the command for the first time you're creating any GCP resource. The command will remember the project ID for subsequent calls.&#x20;

### 🧹 Destroying deployed stack components

You can destroy a stack component using the `destroy` subcommand. For example, to destroy an S3 artifact store you had previously created, you could run:

```shell
zenml artifact-store destroy s3_artifact_store
```
