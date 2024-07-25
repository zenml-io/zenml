---
description: Individually deploying different stack components.
---

# ⚒️ Deploying stacks and components using `mlstacks`

The first step in running your pipelines on remote infrastructure is to deploy all the components that you would need, like an [MLflow tracking server](../../component-guide/experiment-trackers/mlflow.md),
[Kubeflow orchestrator](../../component-guide/orchestrators/kubeflow.md), and more to your cloud.

This can bring plenty of benefits like scalability, reliability, and collaboration. ZenML eases the path to production by providing a seamless way for all tools to interact with others through the use of abstractions. However, one of the most painful parts of this process, from what we see on our Slack and in general, is the deployment of these stack components.

[`mlstacks`](https://mlstacks.zenml.io/) is a Python package that allows you to quickly spin up MLOps
infrastructure using Terraform. It is designed to be used with
[ZenML](https://zenml.io), but can be used with any MLOps tool or platform. You
can deploy a modular MLOps stack for AWS, GCP or K3D using mlstacks. Each deployment type is designed to offer a great deal of flexibility in configuring the resources while preserving the ease of application through the use of sensible defaults.

To make even this process easier for our users, we have created the `deploy` command in `zenml`, which allows you to quickly get started with a full-fledged MLOps stack using only a few commands. You can choose to deploy individual stack components through the stack-component CLI or deploy a stack with multiple components together (a tad more manual steps).

Check out [the full documentation for the mlstacks package](https://mlstacks.zenml.io/) for more information.

## When should I deploy something using mlstacks?

{% hint style="info" %}
**MLStacks deploys resources using a Kubernetes cluster, which may be expensive and not for every user. In order to use stacks which are more basic and cheaper on the cloud, read [how to easily register a cloud stack](../../how-to/stack-deployment/register-a-cloud-stack.md)
if you have existing infrastructure, or read [how to deploy a cloud stack in one click](../../how-to/stack-deployment/deploy-a-cloud-stack.md).**

Or simply try running one of:

```shell
zenml stack register --provider aws
zenml stack deploy --provider aws
```
{% endhint %}

To answer this question, here are some pros and cons in comparison to the stack-component deploy method which can help you choose what works best for you!

{% tabs %}
{% tab title="😍 Pros" %}
* Offers a lot of flexibility in what you deploy.
* Deploying with `mlstacks` gives you a full MLOps stack as the output. Your
  components and stack is automatically imported to ZenML. This saves you the
  effort of manually registering all the components.
{% endtab %}

{% tab title="😥 Cons" %}
* Currently only supports AWS, GCP, and K3D as providers.
* Most stack deployments are Kubernetes-based which might be too heavy for your
  needs.
* Not all stack components are supported yet.
{% endtab %}
{% endtabs %}

The ZenML CLI has special subcommands that allow you to deploy individual stack components as well as whole stacks using MLStacks. These stacks will be useful for you if:

* You are at the start of your MLOps journey, and would like to explore different tools.
* You are looking for guidelines for production-grade deployments.

## How does `mlstacks` work?

MLStacks is built around the concept of a stack specification. A stack specification is a YAML file that describes the stack and includes references to component specification files. A component specification is a YAML file that describes a component. (Currently all deployments of components (in various combinations) must be defined within the context of a stack.)

ZenML handles the creation of stack specifications for you when you run one of the `deploy` subcommands using the CLI. A valid specification is generated and used by `mlstacks` to deploy your stack using Terraform. The Terraform definitions and state are stored in your global configuration directory along with any state files generated while deploying your stack.

Your configuration directory could be in a number of different places depending on your operating system, but read more about it in the [Click docs](https://click.palletsprojects.com/en/8.1.x/api/#click.get\_app\_dir) to see which location applies to your situation.

## Installing the mlstacks extra

To install `mlstacks`, either run `pip install mlstacks` or `pip install "zenml[mlstacks]"` to install it along with ZenML.

MLStacks uses Terraform on the backend to manage infrastructure. You will need to have Terraform installed. Please visit [the Terraform docs](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform) for installation instructions.

MLStacks also uses Helm to deploy Kubernetes resources. You will need to have Helm installed. Please visit [the Helm docs](https://helm.sh/docs/intro/install/#from-script) for installation instructions.

## Deploying a stack

Deploying an end-to-end stack through the ZenML CLI is only possible with the [deployment wizard which does not use `mlstacks`](../../how-to/stack-deployment/deploy-a-cloud-stack.md). However, you can use `mlstacks` directly to deploy various types of stacks and [import them into ZenML](https://mlstacks.zenml.io/reference/zenml).

```shell
zenml stack import -f <path-to-stack-file-generated-by-mlstacks.yaml>
```

## Deploying a stack component

If you have used ZenML before, you must be familiar with the flow of registering new stack components. It goes something like this:

```shell
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

### Destroying a stack component

Destroying a stack component (i.e. deleting and destroying the underlying
infrastructure) is as easy as deploying one. You can run the following command
to destroy the artifact store we created above:

```bash
zenml artifact-store destroy -p gcp my_store
```

This will destroy the deployed infrastructure and prompt you if you also want to remove and deregister the component from your ZenML server.

### 🍨 Available flavors for stack components

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

#### ✨ Customizing your stack components

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
