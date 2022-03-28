---
description: Execute individual steps in specialized environments.
---

# Run steps in specialized environments with step operators

The step operator defers the execution of individual steps in a pipeline to specialized runtime environments that are optimized for Machine Learning workloads. This is helpful when there is a requirement for specialized cloud backends ✨ for different steps. One example could be using powerful GPU instances for training jobs or distributed compute for ingestion streams.

While an orchestrator defines how and where your entire pipeline runs, a step operator defines how and where an individual 
step runs. This can be useful in a variety of scenarios. An example could be if one step within a pipeline should run on a 
separate environment equipped with a GPU (like a trainer step).

An operator can be registered as follows:

```bash
zenml step-operator register OPERATOR_NAME \
    --type=OPERATOR_TYPE
    ...
```

```python
@step(custom_step_operator=OPERATOR_NAME)
def trainer(...) -> ...:
    """Train a model"""
    # This step will run in environment specified by operator
```

## Pre-built Step Operators

ZenML has support for some pre-built step operators, namely:

- AWS Sagemaker 
- AzureML
- Vertex AI

These operators are all to be used for the use-case of running a training job on specialized cloud backends.

{% tabs %}
{% tab title="AzureML" %}
* First, you require a `Machine learning` [resource on Azure](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources). 
If you don't already have one, you can create it through the `All resources` 
page on the Azure portal. 
* Once your resource is created, you can head over to the `Azure Machine 
Learning Studio` and [create a compute cluster](https://docs.microsoft.com/en-us/azure/machine-learning/quickstart-create-resources#cluster) 
to run your pipelines. 
* Next, you will need an `environment` for your pipelines. You can simply 
create one following the guide [here](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-manage-environments-in-studio).
* Finally, we have to set up our artifact store. In order to do this, we need 
to [create a blob container](https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-portal)
on Azure. 

Optionally, you can also create a [Service Principal for authentication](https://docs.microsoft.com/en-us/azure/developer/java/sdk/identity-service-principal-auth). 
This might especially be useful if you are planning to orchestrate your 
pipelines in a non-local setup such as Kubeflow where your local authentication 
won't be accessible.

The command to register the stack component would look like the following. More details about the parameters that you can configure can be found in the class definition of Azure Step Operator in the API docs (https://apidocs.zenml.io/). 

```bash
zenml step-operator register azureml \
    --type=azureml \
    --subscription_id=<AZURE_SUBSCRIPTION_ID> \
    --resource_group=<AZURE_RESOURCE_GROUP> \
    --workspace_name=<AZURE_WORKSPACE_NAME> \
    --compute_target_name=<AZURE_COMPUTE_TARGET_NAME> \
    --environment_name=<AZURE_ENVIRONMENT_NAME> 
```

{% endtab %}

{% tab title="Amazon SageMaker" %}
* First, you need to create a role in the IAM console that you want the jobs running in Sagemaker to assume. This role should at least have the `AmazonS3FullAccess` and `AmazonSageMakerFullAccess` policies applied. Check [this link](https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-roles.html#sagemaker-roles-create-execution-role) to learn how to create a role.

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here](https://docs.aws.amazon.com/sagemaker/latest/dg/notebooks-available-instance-types.html).

* Optionally, you can choose an S3 bucket to which Sagemaker should output any artifacts from your training run. 

* You can also supply an experiment name if you have one created already. Check [this guide](https://docs.aws.amazon.com/sagemaker/latest/dg/experiments-create.html) to know how. If not provided, the job runs would be independent.

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs in Sagemaker. 

* You need to have the `aws` cli set up with the right credentials. Make sure you have the permissions to create and manage Sagemaker runs. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Sagemaker will run.

Once you have all these values handy, you can proceed to setting up the components required for your stack.

The command to register the stack component would look like the following. More details about the parameters that you can configure can be found in the class definition of Sagemaker Step Operator in the API docs (https://apidocs.zenml.io/). 

```bash
zenml step-operator register sagemaker \
    --type=sagemaker
    --role=<SAGEMAKER_ROLE> \
    --instance_type=<SAGEMAKER_INSTANCE_TYPE>
    --base_image=<CUSTOM_BASE_IMAGE>
    --bucket_name=<S3_BUCKET_NAME>
    --experiment_name=<SAGEMAKER_EXPERIMENT_NAME>
```

{% endtab %}

{% tab title="GCP Vertex AI" %}

* You need to have the `gcp` cli set up with the right credentials. Make sure you have the permissions to create and manage Vertex AI custom jobs. Preferably, you should create a [service account](https://cloud.google.com/iam/docs/service-accounts) with the right permissions to create Vertex AI jobs (`roles/aiplatform.admin`) and push to the Artifact/Container registry (`roles/(roles/storage.admin`). Then set the `GOOGLE_APPLICATION_CREDENTIALS` env variable to point to the service account file. 

* Next, you need to choose what instance type needs to be used to run your jobs. You can get the list [here]( https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types).

* You can choose a [GCP bucket](https://cloud.google.com/storage/docs/creating-buckets) to which Vertex should output any artifacts from your training run. 

* You can also choose a custom docker image that you want ZenML to use as a base image for creating an environment to run your jobs on Vertex AI. 

* A container registry has to be configured in the stack. This registry will be used by ZenML to push your job images that Vertex will use. Check out the [cloud guide](../features/guide-aws-gcp-azure.md) to learn how you can set up an GCP container registry. 

Once you have all these values handy, you can proceed to setting up the components required for your stack.

The command to register the stack component would look like the following. More details about the parameters that you can configure can be found in the class definition of Vertex Step Operator in the API docs (https://apidocs.zenml.io/). 

```bash
zenml step-operator register vertex \
    --type=vertex \
    --project=zenml-core \
    --service_account_path=... \
    --region=europe-west1 \
    --machine_type=n1-standard-4 \
    --base_image=<CUSTOM_BASE_IMAGE> \
    --accelerator_type=...
```

{% endtab %}
{% endtabs %}

A concrete example of using these step operators can be found in the [GitHub repository](https://github.com/zenml-io/zenml/tree/main/examples)

## Building your own StepOperator

To have ZenML run your steps in your own backend, all you need to do is implement the [BaseStepOperator](https://apidocs.zenml.io) class with the code that sets up your environment and submits the ZenML entrypoint command to it. 

```python
class BaseStepOperator(StackComponent, ABC):
    """Base class for all ZenML step operators."""

    ...
        ...
    @abstractmethod
    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> None:
        """Abstract method to execute a step.
        Concrete step operator subclasses must implement the following
        functionality in this method:
        - Prepare the execution environment and install all the necessary
          `requirements`
        - Launch a **synchronous** job that executes the `entrypoint_command`
        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            entrypoint_command: Command that executes the step.
            requirements: List of pip requirements that must be installed
                inside the step operator environment.
        """
        # Write custom logic here.
```

The launch method is what gets called when ZenML is executing your step and it is responsible for any logic that pertains to your custom backend.