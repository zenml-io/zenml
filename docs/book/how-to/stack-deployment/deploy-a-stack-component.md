---
description: Individually deploying different stack components.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Deploy a stack component

If you have used ZenML before, you must be familiar with the flow of registering new stack components. It goes something like this:

```
zenml artifact-store register my_store --flavor=s3 --path=s3://my_bucket
```

Commands like these assume that you already have the stack component deployed. In this case, it would mean that you must already have a bucket called `my_bucket` on AWS S3 to be able to use this component.

We took inspiration from this design to build something that feels natural to use and is also sufficiently powerful to take care of the deployment of the respective stack components for you. This is where the \<STACK\_COMPONENT> `deploy` CLI comes in!

The `deploy` command allows you to deploy individual components of your MLOps stack with a single command 🚀. You can also customize your components easily by passing in flags (more on that later).

{% hint style="info" %}
To install `mlstacks`, either run `pip install mlstacks` or `pip install "zenml[mlstacks]"` to install it along with ZenML.

MLStacks uses Terraform on the backend to manage infrastructure. You will need to have Terraform installed. Please visit [the Terraform docs](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform) for installation instructions.

MLStacks also uses Helm to deploy Kubernetes resources. You will need to have Helm installed. Please visit [the Helm docs](https://helm.sh/docs/intro/install/#from-script) for installation instructions.
{% endhint %}

For example, to deploy an artifact store on a GCP account, you can run:

{% code overflow="wrap" %}
```bash
# after installing mlstacks
zenml artifact-store deploy -f gcp -p gcp -r us-east1 -x project_id=zenml my_store
```
{% endcode %}

The command above takes in the following parameters:

* **Name**: The name of the stack component. In this case, it is `my_store`.
* **Flavor:** The flavor of the stack component to deploy. Here, we are deploying an artifact store with the `gcp` flavor.
* **Provider:** The provider to deploy this stack component on. Currently, only **GCP, AWS, and K3D** are supported as providers.
* **Region**: The region to deploy the stack component in.
* **Extra Config:** Some components can be customized by the user and these settings are passed as flags to the command. In the example above, we pass the GCP project ID to select what project to deploy the component to.

Successful execution of this command does the following:

* It also automatically registers the deployed stack component with your ZenML server, so you don't have to worry about manually configuring components after the deployment! 🤩

{% hint style="info" %}
The command currently uses your local credentials for GCP and AWS to provision resources. Integration with your ZenML connectors might be possible soon too!
{% endhint %}

<details>

<summary>Want to know what happens in the background?</summary>

The stack component deploy CLI is powered by ZenML's [mlstacks](https://github.com/zenml-io/mlstacks) in the background. This allows you to configure and deploy select stack components.

Using the values you pass for the cloud, the CLI picks up the right modular recipe to use (one of AWS, GCP, or K3D) and then deploys that recipe with the specific stack component enabled.

</details>

## Destroying a stack component

Destroying a stack component (i.e. deleting and destroying the underlying
infrastructure) is as easy as deploying one. You can run the following command
to destroy the artifact store we created above:

```bash
zenml artifact-store destroy -p gcp my_store
```

This will destroy the deployed infrastructure and prompt you if you also want to remove and deregister the component from your ZenML server.

## 🍨 Available flavors for stack components

Here's a table of all the flavors that can be deployed through the CLI for every stack component. This is a list that will keep on growing and you can also contribute any flavor or stack component that you feel is missing. Refer to the [Contribution page](../../../../CONTRIBUTING.md) for steps on how to do that :smile:

<details>

<summary>How does flavor selection work in the background?</summary>

Whenever you pass in a flavor to any stack-component deploy function, the combination of these two parameters is used to construct a variable name in the following format:

```
enable_<STACK_COMPONENT>_<FLAVOR>
```

This variable is then passed as input to the underlying modular recipe. If you check the [`variables.tf`](https://github.com/zenml-io/mlstacks/blob/main/gcp-modular/variables.tf) file for a given recipe, you can find all the supported flavor-stack component combinations there.

</details>

| Component Type     | Flavor(s)                            |
| ------------------ | ------------------------------------ |
| Artifact Store     | s3, gcp, minio                       |
| Container Registry | aws, gcp                             |
| Experiment Tracker | mlflow                               |
| Orchestrator       | kubernetes, kubeflow, tekton, vertex |
| MLOps Platform     | zenml                                |
| Model Deployer     | seldon                               |
| Step Operator      | sagemaker, vertex                    |

### ✨ Customizing your stack components

With simplicity, we didn't want to compromise on the flexibility that this deployment method allows. As such, we have added the option to pass configuration specific to the stack components as key-value arguments to the deploy CLI. Here is an assortment of all possible configurations that can be set.

<details>

<summary>How do configuration flags work?</summary>

The flags that you pass to the deploy CLI are passed on as-is to the backing modular recipes as input variables. This means that all the flags need to be defined as variables in the respective recipe.

For example, if you take a look at the [`variables.tf`](https://github.com/zenml-io/mlstacks/blob/main/gcp-modular/variables.tf) file for a modular recipe, like the `gcp-modular` recipe, you can find variables like `mlflow_bucket` that you could potentially pass in.

Validation for these flags does not exist yet at the CLI level, so you must be careful in naming them while calling `deploy`.

All these extra configuration options are passed in with the `-x` option. For example, we already saw this in action above when we passed in the GCP project ID to the artifact store deploy command.

```bash
zenml artifact-store deploy -f gcp -p gcp -r us-east1 -x project_id=zenml my_store
```

Simply pass in as many `-x` flags as you want to customize your stack component.

</details>

**Experiment Trackers**

You can assign an existing bucket to the MLflow experiment tracker by passing the `-x mlflow_bucket=...` configuration:

```shell
zenml experiment-tracker deploy mlflow_tracker --flavor=mlflow -p YOUR_DESIRED_PROVIDER -r YOUR_REGION -x mlflow_bucket=gs://my_bucket
```

**Artifact Stores**

For an artifact store, you can pass `bucket_name` as an argument to the command.

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --provider=aws -r YOUR_REGION -x bucket_name=my_bucket
```

**Container Registries**

For container registries, you can pass the repository name using `repo_name`:

```bash
zenml container-registry deploy aws_registry --flavor=aws -p aws -r YOUR_REGION -x repo_name=my_repo
```

This is only useful for the AWS case since AWS requires a repository to be created before pushing images to it and the deploy command ensures that a repository with the name you provide is created. In case of GCP and other providers, you can choose the repository name at the same time as you are pushing the image via code. This is achieved through setting the `target_repo` attribute of [the `DockerSettings` object](../customize-docker-builds/README.md).

#### Other configuration

* In the case of GCP components, it is _required_ that you pass a project ID to the command as extra configuration when you're creating any GCP resource.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
