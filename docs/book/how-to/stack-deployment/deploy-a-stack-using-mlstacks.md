---
description: Deploying an entire stack with mlstacks.
---

# Deploy a stack using mlstacks

[`mlstacks`](https://mlstacks.zenml.io/) is a Python package that allows you to quickly spin up MLOps
infrastructure using Terraform. It is designed to be used with
[ZenML](https://zenml.io), but can be used with any MLOps tool or platform. You
can deploy a modular MLOps stack for AWS, GCP or K3D using mlstacks. Each deployment type is designed to offer a great deal of flexibility in configuring the resources while preserving the ease of application through the use of sensible defaults.

Check out [the full documentation for the mlstacks package](https://mlstacks.zenml.io/) for more information.

## When should I deploy something using mlstacks?

To answer this question, here are some pros and cons in comparison to [the stack-component deploy method](deploy-a-stack-component.md) which can help you choose what works best for you!

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

## Installing the mlstacks extra

To install `mlstacks`, either run `pip install mlstacks` or `pip install
"zenml[mlstacks]"` to install it along with ZenML.

MLStacks uses Terraform on the backend to manage infrastructure. You will need
to have Terraform installed. Please visit [the Terraform
docs](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform)
for installation instructions.

MLStacks also uses Helm to deploy Kubernetes resources. You will need to have
Helm installed. Please visit [the Helm
docs](https://helm.sh/docs/intro/install/#from-script) for installation
instructions.

## Deploying a stack

A simple stack deployment can be done using the following command:

```bash
zenml stack deploy -p aws -a -n basic -r eu-north-1 -x bucket_name=my_bucket -o sagemaker
```

This command deploys a stack on AWS that uses an S3 bucket as an artifact store
and Sagemaker as your orchestrator. The stack will be imported into ZenML once
the deployment is complete and you can start using it right away!

Supported flavors and component types are as follows:

| Component Type | Flavor(s) |
| -------------- | --------- |
| Artifact Store | s3, gcp, minio |
| Container Registry | aws, gcp |
| Experiment Tracker | mlflow |
| Orchestrator | kubernetes, kubeflow, tekton, vertex |
| MLOps Platform | zenml |
| Model Deployer | seldon |
| Step Operator | sagemaker, vertex |

MLStacks currently only supports deployments using AWS, GCP, and K3D as providers.

<summary>Want more details on how this works internally?</summary>

The stack recipe CLI interacts with the
[mlstacks](https://github.com/zenml-io/mlstacks) repository to fetch the recipes
and stores them locally in the **Global Config** directory. 

This is where you could potentially make any changes you want to the recipe files. You can also use native terraform commands like `terraform apply` to deploy components but this would require you to pass the variables manually using the `-var-file` flag to the terraform CLI.

</details>

### CLI Options for `zenml stack deploy`

Current required options to be passed in to the `zenml stack deploy` subcommand
are:

- `-p` or `--provider`: The cloud provider to deploy the stack on. Currently
  supported providers are `aws`, `gcp`, and `k3d`.
- `-n` or `--name`: The name of the stack to be deployed. This is used to
  identify the stack in ZenML.
- `-r` or `--region`: The region to deploy the stack in.

The remaining options relate to which components you want to deploy.

If you want to pass an `mlstacks` stack specification file into the CLI to use
for deployment, you can do so with the `-f` option. Similarly, if you wish to
see more of the Terraform logging, prompts and output, you can pass the `-d`
flag to turn on `debug-mode`.

Any extra configuration for specific components (as noted [in the individual
component deployment documentation](deploy-a-stack-component.md)) can be passed
in with the `-x` option. This option can be used multiple times to pass in
multiple configurations.

### Interactive stack deployment

If you would like to be guided through the deployment process, you can use the
`zenml stack deploy` command with the `--interactive` flag. You will still need
to provide the `provider`, `name` and `region` options as described above but
for the rest, you will get prompts in the CLI as to which components you would
like to deploy. For example, using GCP as the provider you might type:

```bash
zenml stack deploy -p gcp -n my_new_stack -r us-east1 --interactive
```

## Displaying Terraform outputs for stacks deployed with mlstacks

If you want to view any of the Terraform-generated outputs for a stack deployed
with `mlstacks`, you can do so with the following command:

```bash
zenml stack describe -o <STACK_NAME>
```

This will print any available outputs to the console if you have deployed a
stack with `mlstacks` via ZenML.

## Deleting / destroying resources

🗑️ Once you're done running your pipelines, there's only a single command you need to execute that will take care of cleaning up all the resources that you had created on your cloud.

```
zenml stack destroy <STACK_NAME>
```

This will offer you the option to delete the underlying stack specifications and
state files as well. You can also choose to delete the stack from your ZenML
server.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
