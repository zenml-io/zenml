---
description: Individually deploying different stack components.
---

# Deploy a stack component

If you have used ZenML before, you must be familiar with the flow of registering new stack components. It goes something like this:

```
zenml artifact-store register my_store --flavor=s3 --path=s3://my_bucket
```

Commands like these assume that you already have the stack component deployed. In this case, it would mean that you must already have a bucket called `my_bucket` on AWS S3 to be able to use this component.

We took inspiration from this design to build something that feels natural to use and is also sufficiently powerful to take care of the deployment of the respective stack components for you. This is where the \<STACK\_COMPONENT> `deploy` CLI comes in!

The `deploy` command allows you to deploy individual components of your MLOps stack with a single command 🚀. You can also customize your components easily by passing in flags (more on that later).

For example, to deploy an MLflow tracking server on a GCP account, you can run:

{% code overflow="wrap" %}
```bash
zenml experiment-tracker deploy my_tracker --flavor=mlflow --cloud=gcp --project_id="zenml"
```
{% endcode %}

The command above takes in the following parameters:

* **Name**: The name of the stack component. In this case, it is `my_tracker` . If you don't provide a name, a random one is generated for you.
* **Flavor:** The flavor of the stack component to deploy. Here, we are deploying an MLflow experiment tracker.
* **Cloud:** The cloud to deploy this stack component on. Currently, only **GCP, AWS, and k3d** are supported as providers).
* **Additional Configuration:** Some components can be customized by the user and these settings are passed as flags to the command. In the example above, we pass the GCP project ID to select what project to deploy the component to.

Successful execution of this command does the following:

* Asks for your confirmation on the resources that will be deployed.
* Once you agree, it starts the deployment process and gives you a list of outputs at the end pertaining to your deployed stack component (the text in green in the screenshot below).
* It also automatically registers the deployed stack component with your ZenML server, so you don't have to worry about manually configuring components after the deployment! 🤩

![Deploying an artifact store](../../../.gitbook/assets/artifact\_store\_deploy.png)

{% hint style="info" %}
The command currently uses your local credentials for GCP and AWS to provision resources. Integration with your ZenML connectors might be possible soon too!
{% endhint %}

<details>

<summary>Want to know what happens in the background?</summary>

The stack component deploy CLI is powered by ZenML's [Stack Recipes](https://github.com/zenml-io/mlops-stacks) in the background, more specifically the [new modular recipes](https://github.com/zenml-io/mlops-stacks/releases/tag/0.6.0). These allow you to configure and deploy select stack components as opposed to deploying the full stack, as with the legacy stack recipes.

Using the values you pass for the cloud, the CLI picks up the right modular recipe to use (one of AWS, GCP, or k3d) and then deploys that recipe with the specific stack component enabled.

The recipe files live in the Global Config directory under the `deployed_stack_components` directory.

</details>

![The workflow behind running a stack-component deploy command](../../../.gitbook/assets/zenml\_stack-component\_deploy.png)

### 🍨 Available flavors for stack components

Here's a table of all the flavors that can be deployed through the CLI for every stack component. This is a list that will keep on growing and you can also contribute any flavor or stack component that you feel is missing. Refer to the [Contribution page](contribute-flavors-or-components.md) for steps on how to do that :smile:

<details>

<summary>How does flavor selection work in the background?</summary>

Whenever you pass in a flavor to any stack-component deploy function, the combination of these two parameters is used to construct a variable name in the following format:

```
enable_<STACK_COMPONENT>_<FLAVOR>
```

This variable is then passed as input to the underlying modular recipe. If you check the [`variables.tf`](https://github.com/zenml-io/mlops-stacks/blob/main/gcp-modular/variables.tf) file for a given recipe, you can find all the supported flavor-stack component combinations there.

</details>

<table><thead><tr><th width="374">Component Type</th><th>Flavor</th></tr></thead><tbody><tr><td>Experiment Tracker</td><td>mlflow</td></tr><tr><td>Model Deployer</td><td>seldon</td></tr><tr><td>Artifact Store</td><td>s3</td></tr><tr><td></td><td>gcs</td></tr><tr><td></td><td>minio</td></tr><tr><td>Orchestrator</td><td>kubernetes</td></tr><tr><td></td><td>kubeflow</td></tr><tr><td></td><td>tekton</td></tr><tr><td></td><td>sagemaker</td></tr><tr><td></td><td>vertex</td></tr><tr><td>Step Operator</td><td>sagemaker</td></tr><tr><td></td><td>vertex</td></tr><tr><td>Container Registry</td><td>gcr</td></tr><tr><td></td><td>ecr</td></tr><tr><td></td><td>k3d-registry</td></tr></tbody></table>

### ✨ Customizing your stack components

With simplicity, we didn't want to compromise on the flexibility that this deployment method allows. As such, we have added the option to pass configuration specific to the stack components as key-value arguments to the deploy CLI. Here is an assortment of all possible configurations that can be set.

<details>

<summary>How do configuration flags work?</summary>

The flags that you pass to the deploy CLI are passed on as-is to the backing modular recipes as input variables. This means that all the flags need to be defined as variables in the respective recipe.

For example, if you take a look at the [`variables.tf`](https://github.com/zenml-io/mlops-stacks/blob/main/gcp-modular/variables.tf) file for a modular recipe, like the `gcp-modular` recipe, you can find variables like `mlflow_bucket` that correspond to the `--mlflow-bucket` flag that can be passed to the experiment tracker's deploy CLI.

Validation for these flags does not exist yet at the CLI level, so you must be careful in naming them while calling `deploy`.

</details>

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

For container registries, you can pass the repository name using `repo_name`:

```bash
zenml container-registry deploy aws_registry --flavor=aws --repo_name=my_repo
```

This is only useful for the AWS case since AWS requires a repository to be created before pushing images to it and the deploy command ensures that a repository with the name you provide is created. In case of GCP and other providers, you can choose the repository name at the same time as you are pushing the image via code. This is achieved through setting the `target_repo` attribute of [the `DockerSettings` object](../../user-guide/advanced-guide/environment-management/containerize-your-pipeline.md).

#### Other configuration

* You can also pass a region to deploy your resources to in the case of AWS and GCP recipes. For example, to deploy an S3 artifact store in the `us-west-2` region, you can run:

<pre class="language-bash"><code class="lang-bash"><strong>zenml artifact-store deploy s3_artifact_store --flavor=s3 --region=us-west-2
</strong></code></pre>

The default region is `eu-west-1` for AWS and `europe-west1` for GCP.

{% hint style="warning" %}
Changing regions is not recommended as it can lead to unexpected results for components that share infrastructure like Kubernetes clusters. If you must do so, please destroy all the stack components from the older region by running the `destroy` command and then redeploy using the `deploy` command.
{% endhint %}

* In the case of GCP components, it is _required_ that you pass a project ID to the command for the first time you're creating any GCP resource. The command will remember the project ID for subsequent calls.

### 🧹 Destroying deployed stack components

You can destroy a stack component using the `destroy` subcommand. For example, to destroy an S3 artifact store you had previously created, you could run:

```shell
zenml artifact-store destroy s3_artifact_store
```

<details>

<summary>How does ZenML know where my component is deployed?</summary>

When you create a component using the `deploy` CLI, ZenML attaches some labels to your component, specifically, a `cloud` label that tells it what cloud your component is deployed on.

This in turn, helps ZenML to figure out what modular recipe to use to destroy your deployed component.

You can check the labels attached to your stack components by running:

```
zenml <STACK_COMPONENT> describe <NAME>
```

</details>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>

