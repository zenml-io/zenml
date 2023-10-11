---
description: How to orchestrate pipelines with Amazon Sagemaker
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Sagemaker orchestrator is an [orchestrator](./orchestrators.md) flavor provided
with the ZenML `aws` integration that uses [Amazon Sagemaker Pipelines](https://sagemaker-examples.readthedocs.io/en/latest/sagemaker-pipelines/index.html)
to run your pipelines.

{% hint style="warning" %}
This component is only meant to be used within the context of [remote ZenML deployment scenario](../../getting-started/deploying-zenml/deploying-zenml.md). Usage with a local ZenML deployment may lead to unexpected behavior!
{% endhint %}

## When to use it

You should use the Sagemaker orchestrator if:
* you're already using AWS.
* you're looking for a proven production-grade orchestrator.
* you're looking for a UI in which you can track your pipeline runs.
* you're looking for a managed solution for running your pipelines.
* you're looking for a serverless solution for running your pipelines.

## How to deploy it

In order to use a Sagemaker AI orchestrator, you need to first deploy [ZenML to the
cloud](../../getting-started/deploying-zenml/deploying-zenml.md). It would be
recommended to deploy ZenML in the same region as you plan on using for
Sagemaker, but it is not necessary to do so. You must ensure that you are
[connected to the remote ZenML
server](../../starter-guide/collaborate/zenml-deployment.md) before using this
stack component.

The only other thing necessary to use the ZenML Sagemaker orchestrator is
enabling the relevant permissions for your particular role.

In order to quickly enable APIs, and create other resources necessary for to use
this integration, we will soon provide a Sagemaker stack
recipe via [our `mlops-stacks` recipe repository](https://github.com/zenml-io/mlops-stacks), which
will help you set up the infrastructure with one click.

## How to use it

To use the Sagemaker orchestrator, we need:

* The ZenML `aws` and `s3` integrations installed. If you haven't done so, run 

```shell
zenml integration install aws s3
```

* [Docker](https://www.docker.com) installed and running.
* A [remote artifact store](../artifact-stores/artifact-stores.md) as part of 
your stack (configured with an `authentication_secret` attribute).
* A [remote container registry](../container-registries/container-registries.md) 
as part of your stack.
* An IAM role or user with [an `AmazonSageMakerFullAccess` managed policy](https://docs.aws.amazon.com/sagemaker/latest/dg/security-iam-awsmanpol.html) applied to it
  as well as `sagemaker.amazonaws.com` added as a Principal Service. Full
  details on these permissions can be found
  [here](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html)
  or use the ZenML recipe (when available) which will set up the necessary
    permissions for you. The creation of this role is described in more detail
    [in the instructions](https://github.com/zenml-io/zenml/tree/main/examples/sagemaker_orchestration) for using our `sagemaker_orchestration` example.
* The local client (whoever is running the pipeline) will also have to have the
  necessary permissions or role to be able to launch Sagemaker jobs. (This would
  be covered by the `AmazonSageMakerFullAccess` policy suggested above.)

We can then register the orchestrator and use it in our active stack:
```shell
zenml orchestrator register <ORCHESTRATOR_NAME> \
    --flavor=sagemaker --execution_role=<YOUR_ROLE_ARN>

# Register and activate a stack with the new orchestrator
zenml stack register <STACK_NAME> -o <ORCHESTRATOR_NAME> ... --set
```

{% hint style="info" %}
ZenML will build a Docker image called `<CONTAINER_REGISTRY_URI>/zenml:<PIPELINE_NAME>`
which includes your code and use it to run your pipeline steps in Sagemaker. 
Check out [this page](../../advanced-guide/pipelines/containerization.md)
if you want to learn more about how ZenML builds these images and
how you can customize them.
{% endhint %}

You can now run any ZenML pipeline using the Sagemaker orchestrator:
```shell
python file_that_runs_a_zenml_pipeline.py
```

### Run pipelines on a schedule

The ZenML Sagemaker orchestrator doesn't currently support running pipelines on
a schedule. We maintain a public roadmap for ZenML, which you can find
[here](https://zenml.io/roadmap). We welcome community contributions (see more
[here](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md)) so if you
want to enable scheduling for Sagemaker, please [do let us
know](https://zenml.io/slack-invite)!

### Additional configuration

For additional configuration of the Sagemaker orchestrator, you can pass
`SagemakerOrchestratorSettings` which allows you to configure (among others) the following attributes:

* `instance_type`: The instance type to use for the Sagemaker training job.
  (Defaults to `ml.t3.medium`.)
* `processor_role`: The IAM role to use for the Sagemaker processing job/step.
* `volume_size_in_gb`: The size of the volume to use for the Sagemaker training
  job. (Defaults to 30 GB.)
* `max_runtime_in_seconds`: The maximum runtime of the Sagemaker training job.
  (Defaults to 1 day or 86400 seconds.)
* `processor_tags`: Any tags you want to add to the particular step or pipeline
  as a whole.

Check out the [this docs page](../..//advanced-guide/pipelines/settings.md)
for more information on how to specify settings.

A concrete example of using the Sagemaker orchestrator can be found 
[here](https://github.com/zenml-io/zenml/tree/main/examples/sagemaker_orchestration).

For more information and a full list of configurable attributes of the Sagemaker 
orchestrator, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-aws/#zenml.integrations.aws.orchestrators.sagemaker_orchestrator.SagemakerOrchestrator).

### Enabling CUDA for GPU-backed hardware

Note that if you wish to use this orchestrator to run steps on a GPU, you will
need to follow [the instructions on this
page](../../advanced-guide/pipelines/gpu-hardware.md) to ensure that it works.
It requires adding some extra settings customization and is essential to enable
CUDA for the GPU to give its full acceleration.
