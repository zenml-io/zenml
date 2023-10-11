---
description: Introduction to Stack recipes which help you deploy a full MLOps stack in minutes!
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


When we first created ZenML as an extensible MLOps framework for creating portable, production-ready MLOps pipelines, we saw many of our users having to deal with the pain of deploying infrastructure from scratch to run these pipelines.

The expertise of setting up these often-complex stacks up shouldn't be a prerequisite to running your ML pipelines. We created stack recipes as a way to allow you to quickly get started with a full-fledged MLOps stack with the execution of just a couple of simple commands. Read on to learn what a recipe is, how you can deploy it and the steps needed to create your own!

## Stack Recipes 🍱

A Stack Recipe is a collection of carefully-crafted Terraform modules and resources which, when executed, creates a range of stack components that can be used to run your pipelines. Each recipe is designed to offer a great deal of flexibility in configuring the resources while preserving the ease of application through the use of sensible defaults.

Check out the full list of available recipes at the [mlops-stacks repository](https://github.com/zenml-io/mlops-stacks#-list-of-recipes).

### Deploying a recipe 🚀

Detailed steps are available [in the
README](https://github.com/zenml-io/mlops-stacks#-list-of-recipes) of the
respective stack's recipe but here's what a simple flow could look like:

1. 📃 List the available recipes in the repository.

    ```
    zenml stack recipe list
    ```

2. Pull the recipe that you wish to deploy to your local system.

    ```
    zenml stack recipe pull <STACK_RECIPE_NAME>
    ``` 

3. 🎨 Customize your deployment by editing the default values in the `locals.tf` file. This file holds all the configurable parameters for each of the stack components.

4. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

5. 🚀 Deploy the recipe with this simple command.

    ```
    zenml stack recipe deploy <STACK_RECIPE_NAME>
    ```

    If you want to allow ZenML to automatically import the created resources as a ZenML stack, pass the `--import` flag to the command above.
    By default, the imported stack will have the same name as the stack recipe and
    you can provide your own custom name with the `--stack-name` option.


6. You'll notice that a ZenML stack configuration file gets created after the previous command executes 🤯! This YAML file can be imported as a ZenML stack manually by running the following command.

    ```
    zenml stack import <STACK_NAME> -f <PATH_TO_THE_CREATED_STACK_CONFIG_YAML>
    ```

### Deleting resources

1. 🗑️ Once you're done running your pipelines, there's only a single command you need to execute that will take care of cleaning up all the resources that you had created on your cloud.

    ```
    zenml stack recipe destroy <STACK_RECIPE_NAME>
    ```

2. (Optional) 🧹 You can also remove all the downloaded recipe files from the `pull` execution by using the `clean` command.

    ```
    zenml stack recipe clean
    ```

Check out the [API docs](https://apidocs.zenml.io/) to learn more about each of these commands and the options that are available.

## Deploying stack components directly

To deploy stack components directly without needing to pull stack recipes (as
described above), you can use the `zenml <STACK_COMPONENT> deploy` command. For
example, to deploy an S3 artifact store, you can run:

```shell
zenml artifact-store deploy s3_artifact_store --flavor=s3
```

The command takes in a name to use for the stack component, along with the
flavor and the cloud provider. In case of components like artifact stores and
container registries, the cloud is the same as the flavor and can be omitted
from the command. (Currently, only GCP, AWS and k3d are supported as providers.)

Available flavors that can currently be deployed in this way include:

| Component Type | Flavor |
| -------------- | ------ |
| Experiment Tracker | mlflow |
| Model Deployer | seldon |
|   | kserve |
| Artifact Store | s3 |
|   | gcs |
|   | minio |
| Container Registry | gcr |
|   | ecr |
|   | k3d-registry |
| Orchestrator | kubernetes |
|   | kubeflow |
|   | tekton |
|   | sagemaker |
| Step Operator | sagemaker |
| Secrets Manager | aws |
|   | gcp |

### Customizing the deployment of stack components

You can pass configuration specific to the stack components as key-value
arguments. If you don't provide a name, a random one is generated for you.

#### Experiment Trackers

For
example, to assign an existing bucket to the MLflow experiment tracker, you can
run:

```shell
zenml experiment-tracker deploy mlflow_tracker --flavor=mlflow --mlflow_bucket=gs://my_bucket
```

#### Artifact Stores

For an artifact store, you can pass `bucket_name` as an argument to the command.

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --bucket_name=my_bucket
```

#### Container Registries

For container registries you can pass the repository name using `repo_name`:

```bash
zenml container-registry deploy aws_registry --flavor=aws --repo_name=my_repo
```

This is only useful for the AWS case since AWS requires a repository to be
created before pushing images to it and the deploy command ensures that a
repository with the name you provide is created. In case of GCP and other
providers, you can choose the repository name at the same time as you are
pushing the image via code. This is achieved through setting the `target_repo`
attribute of the [the `DockerSettings` object](../pipelines/settings.md).

{% hint style="info" %}
In the case of GCP components, it is *required* that you pass a project ID to
the command for the first time you're creating any GCP resource. The command
will remember the project ID for subsequent calls. For example, to deploy a GCS
artifact store, you can run:

```bash
zenml artifact-store deploy gcs_artifact_store --flavor=gcs --project_id=my_project
```
{% endhint %}

### Other configuration

You can also pass a region to deploy your resources to in the case of AWS and
GCP recipes. For example, to deploy an S3 artifact store in the `us-west-2`
region, you can run:

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --region=us-west-2
```

The default region is `eu-west-1` for AWS and `europe-west1` for GCP.

{% hint style="warning" %}
Changing regions is not recommended as it can lead to unexpected results for
components that share infrastructure like Kubernetes clusters. If you
must do so, please destroy all the stack components from the
older region by running the `destroy` command and then redeploy using the `deploy`
command.
{% endhint %}

### Destroying deployed stack components

You can destroy a stack component using the `destroy` subcommand. For example,
to destroy an S3 artifact store you had previously created, you could run:

```shell
zenml artifact-store destroy s3_artifact_store
```

## Further Integration with the ZenML CLI 🙏

The ZenML CLI offers a set of commands to make it easy for you to list, pull and deploy recipes from anywhere!

In addition to the underlying `terraform` functionality, these commands also offer the following:

- ability to list all the available recipes conveniently before you choose to deploy any one of them.
- checks to ensure that you have all the binaries/tools installed for running a recipe.
- extensive logs and error messages that guide you in case any of the recipes fails or misbehaves.
- option to automatically import a ZenML stack out of the components created
  after deploying a stack recipe.

To learn more about what you can do with the ZenML CLI, please refer to the [CLI
docs](https://apidocs.zenml.io/latest/cli/).

## Creating your own recipe 🧑‍🍳

The number of recipes available right now is finite and there can be combinations of stack components that are not yet covered by any of the existing recipes. If you wish, you can contribute a recipe for any combination that you'd like to see.

The [`CONTRIBUTING.md`](https://github.com/zenml-io/mlops-stacks/blob/main/CONTRIBUTING.md) file on the repository lists the principles that each recipe follows and gives details about the steps you should take when designing your own recipe. Feel free to also reach out to the ZenML community on [Slack](https://zenml.slack.com/ssb/redirect) 👋 if you need help with any part of the process!

## Manual Recipes with Terraform

You can still use the ZenML stack recipes without needing the `zenml stack recipe` CLI commands or even without installing ZenML. Since each recipe is a group of Terraform modules, you can simply use the Terraform CLI to perform apply and destroy operations.

### Create the stack

1. 🎨 Customize your deployment by editing the default values in the `locals.tf` file.

2. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

3. Initialize Terraform modules and download provider definitions.
    ```shell
    terraform init
    ```

4. Apply the recipe.
    ```shell
    terraform apply
    ```

### Getting the outputs

For outputs that are sensitive, you'll see that they are not shown directly on the logs. To view the full list of outputs, run the following command:

```shell
terraform output
```

To view individual sensitive outputs, use the following format. Here, the metadata password is being obtained.

```shell
terraform output metadata-db-password
```

### Deleting resources (manually)

1. 🗑️ Run the destroy function to clean up all resources.
    ```shell
    terraform destroy
    ```
