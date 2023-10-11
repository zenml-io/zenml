---
description: How to deploy models to Kubernetes with Seldon Core
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Seldon Core Model Deployer is one of the available flavors of the [Model Deployer](./model-deployers.md) 
stack component. Provided with the MLflow integration it can be used to deploy
and manage models on a inference server running on top of a Kubernetes cluster.

## When to use it?

[Seldon Core](https://github.com/SeldonIO/seldon-core) is a production grade
open source model serving platform. It packs a wide range of features built
around deploying models to REST/GRPC microservices that include monitoring and
logging, model explainers, outlier detectors and various continuous deployment
strategies such as A/B testing, canary deployments and more.

Seldon Core also comes equipped with a set of built-in model server
implementations designed to work with standard formats for packaging ML models
that greatly simplify the process of serving models for real-time inference.

You should use the Seldon Core Model Deployer:

* If you are looking to deploy your model on a more advanced infrastructure
  like Kubernetes.

* If you want to handle the lifecycle of the deployed model with no downtime, including updating the runtime graph, scaling, monitoring, and security.

* Looking for more advanced API endpoints to interact with the deployed model, including 
REST and GRPC endpoints.

* If you want more advanced deployment strategies like A/B testing, canary deployments, and more.

* if you have a need for a more complex deployment process which can be customized by the advanced inference graph that includes custom [TRANSFORMER](https://docs.seldon.io/projects/seldon-core/en/latest/workflow/overview.html) and [ROUTER](https://docs.seldon.io/projects/seldon-core/en/latest/analytics/routers.html?highlight=routers#)

If you are looking for a more easy way to deploy your models locally, you can use the [MLflow Model Deployer](./mlflow.md) flavor.

## How to deploy it?

ZenML provides a Seldon Core flavor build on top of the Seldon Core Integration to allow you to deploy and use your models in a production-grade environment. In order to use the integration you need to install it on your local machine to be able to register an Seldon Core
Model deployer with ZenML and add it to your stack:

```bash
zenml integration install seldon-core -y
```

To deploy and make use of the Seldon Core integration we need to have the following prerequisites:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context. You can find more information about setup and usage of the Kubernetes
cluster in the [ZenML Cloud Guide](../../cloud-guide/overview.md)

2. Seldon Core needs to be preinstalled and running in the target Kubernetes
cluster. Check out the [official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup)).

3. models deployed with Seldon Core need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
Seldon Core is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).
You can use one of the supported [remote storage flavors](../artifact-stores/artifact-stores.md) to store your models as part of your stack

Since the Seldon Model Deployer is interacting with the Seldon Core model server deployed on 
a Kubernetes cluster, you need to provide a set of configuration parameters. These parameters are:

* kubernetes_context: the Kubernetes context to use to contact the remote Seldon Core installation. If not specified, the current configuration is used. Depending on where the Seldon model deployer is being used
* kubernetes_namespace: the Kubernetes namespace where the Seldon Core deployment servers 
are provisioned and managed by ZenML. If not specified, the namespace set in the current configuration is used.
* base_url: the base URL of the Kubernetes ingress used to expose the Seldon Core deployment servers.
* secret: the name of a ZenML secret containing the credentials used by Seldon Core storage initializers to authenticate to the Artifact Store


{% hint style="info" %}
Configuring an Seldon Core in a Kubernetes cluster can be a complex and error prone process, so we have provided a set of of Terraform-based recipes to quickly provision popular combinations of MLOps tools. More information about these recipes can be found in the [Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks)
{% endhint %}

### Managing Seldon Core Credentials

The Seldon Core model servers need to access the Artifact Store in the ZenML
stack to retrieve the model artifacts. This usually involve passing some
credentials to the Seldon Core model servers required to authenticate with
the Artifact Store. In ZenML, this is done by creating a ZenML secret with the
proper credentials and configuring the Seldon Core Model Deployer stack component
to use it, by passing the `--secret` argument to the CLI command used
to register the model deployer. We've already done the latter, now all that is
left to do is to configure the `s3-store` ZenML secret specified before as a
Seldon Model Deployer configuration attribute with the credentials needed by
Seldon Core to access the artifact store.

There are built-in secret schemas that the Seldon Core integration provides which
can be used to configure credentials for the 3 main types of Artifact Stores
supported by ZenML: S3, GCS and Azure.

you can use `seldon_s3` for AWS S3 or `seldon_gs` for GCS and `seldon_az` for Azure. To read more about secrets, secret schemas and how they are used in ZenML, please refer to the
[Secrets Manager](../secrets-managers/secrets-managers.md).

The following is an example of registering an S3 secret with the Seldon Core model deployer:

```shell
$ zenml secrets-manager secret register -s seldon_s3 s3-store \
    --rclone_config_s3_env_auth=False \
    --rclone_config_s3_access_key_id='ASAK2NSJVO4HDQC7Z25F' \ --rclone_config_s3_secret_access_key='AhkFSfhjj23fSDFfjklsdfj34hkls32SDfscsaf+' \
    --rclone_config_s3_session_token=@./aws_session_token.txt \
    --rclone_config_s3_region=us-east-1
Expanding argument value rclone_config_s3_session_token to contents of file ./aws_session_token.txt.
The following secret will be registered.
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE ┃
┠────────────────────────────────────┼──────────────┨
┃       rclone_config_s3_type        │ ***          ┃
┃     rclone_config_s3_provider      │ ***          ┃
┃     rclone_config_s3_env_auth      │ ***          ┃
┃   rclone_config_s3_access_key_id   │ ***          ┃
┃ rclone_config_s3_secret_access_key │ ***          ┃
┃   rclone_config_s3_session_token   │ ***          ┃
┃      rclone_config_s3_region       │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials

$ zenml secrets-manager secret get s3-store
INFO:botocore.credentials:Found credentials in shared credentials file: ~/.aws/credentials
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE                           ┃
┠────────────────────────────────────┼────────────────────────────────────────┨
┃       rclone_config_s3_type        │ s3                                     ┃
┃     rclone_config_s3_provider      │ aws                                    ┃
┃     rclone_config_s3_env_auth      │ False                                  ┃
┃   rclone_config_s3_access_key_id   │ ASAK2NSJVO4HDQC7Z25F                   ┃
┃ rclone_config_s3_secret_access_key │ AhkFSfhjj23fSDFfjklsdfj34hkls32SDfscs… ┃
┃   rclone_config_s3_session_token   │ FwoGZXIvYXdzEG4aDHogqi7YRrJyVJUVfSKpA… ┃
┃                                    │                                        ┃
┃      rclone_config_s3_region       │ us-east-1                              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## How do you use it?

We can register the model deployer and use it in our active stack:

```bash
zenml model-deployer register seldon_deployer --flavor=seldon \
  --kubernetes_context=zenml-eks \
  --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST \
  --secret=s3-store-credentials

# Now we can use the model deployer in our stack
zenml stack update seldon_stack --model-deployer=seldon_deployer
```

The following code snippet shows how to use the Seldon Core Model Deployer to deploy a model inside a ZenML pipeline step:

```python
from zenml.artifacts import ModelArtifact
from zenml.environment import Environment
from zenml.integrations.seldon.model_deployers import SeldonModelDeployer
from zenml.integrations.seldon.services.seldon_deployment import (
  SeldonDeploymentConfig,
  SeldonDeploymentService,
)
from zenml.steps import (
  STEP_ENVIRONMENT_NAME,
  StepContext,
  step,
)

@step(enable_cache=True)
def seldon_model_deployer_step(
  context: StepContext,
  model: ModelArtifact,
) -> SeldonDeploymentService:
  model_deployer = SeldonModelDeployer.get_active_model_deployer()

  # get pipeline name, step name and run id
  step_env = Environment()[STEP_ENVIRONMENT_NAME]

  service_config=SeldonDeploymentConfig(
      model_uri=model.uri,
      model_name="my-model",
      replicas=1,
      implementation="TENSORFLOW_SERVER",
      secret_name="seldon-secret",
      pipeline_name = step_env.pipeline_name,
      pipeline_run_id = step_env.pipeline_run_id,
      pipeline_step_name = step_env.step_name,
  )

  service = model_deployer.deploy_model(
      service_config, replace=True, timeout=300
  )

  print(
      f"Seldon deployment service started and reachable at:\n"
      f"    {service.prediction_url}\n"
  )

  return service
```

A concrete example of using the Seldon Core Model Deployer can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment).

For more information and a full list of configurable attributes of the Seldon Core Model Deployer, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.seldon.model_deployers).

## Custom Model Deployment

When you have a custom use-case where Seldon Core pre-packaged inference servers cannot cover your needs, you can leverage the language wrappers to containerise your machine learning model(s) and logic.
With ZenML's Seldon Core Integration, you can create your own custom model
deployment code by creating a custom predict function that will be passed
to a custom deployment step responsible for preparing a Docker image for the
model server.

This `custom_predict` function should be getting the model and the input data as arguments and return the output data. ZenML will take care of loading the model
into memory, starting the `seldon-core-microservice` that will be responsible for serving the model, and running the predict function.

```python
def pre_process(input: np.ndarray) -> np.ndarray:
    """Pre process the data to be used for prediction."""
    pass


def post_process(prediction: np.ndarray) -> str:
    """Pre process the data"""
    pass


def custom_predict(
    model: Any,
    request: Array_Like,
) -> Array_Like:
    """Custom Prediction function.

    The custom predict function is the core of the custom deployment, the function
    is called by the custom deployment class defined for the serving tool.
    The current implementation requires the function to get the model loaded in the memory and
    a request with the data to predict.

    Args:
        model (Any): The model to use for prediction.
        request: The prediction response of the model is an array-like format.
    Returns:
        The prediction in an array-like format. (e.g: np.ndarray, List[Any], str, bytes, Dict[str, Any])
    """
    pass
```

Then this custom predict function `path` can be passed to the custom deployment parameters.

```python
seldon_tensorflow_custom_deployment = seldon_custom_model_deployer_step(
    config=SeldonDeployerStepConfig(
        service_config=SeldonDeploymentConfig(
            model_name="seldon-tensorflow-custom-model",
            replicas=1,
            implementation="custom",
            resources={"requests": {"cpu": "200m", "memory": "500m"}},
        ),
        timeout=240,
        custom_deploy_parameters=CustomDeployParameters(
            predict_function="seldon_tensorflow.steps.tf_custom_deploy_code.custom_predict"
        ),
    )
)
```
The full code example can be found [here](https://github.com/zenml-io/zenml/blob/main/examples/custom_code_deployment/).

### Advanced Custom Code Deployment with Seldon Core Integration

{% hint style="warning" %}
Before creating your custom model class, you should take a look at the
[custom Python model](https://docs.seldon.io/projects/seldon-core/en/latest/python/python_wrapping_docker.html) 
section of the Seldon Core documentation.
{% endhint %}

The built-in Seldon Core custom deployment step is a good starting point for
deploying your custom models. However if you want to deploy more than the
trained model, you can create your own Custom Class and a custom step
to achieve this.

Example of the [custom class](https://apidocs.zenml.io/0.13.0/api_docs/integrations/#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel)

The built-in Seldon Core custom deployment step responsible for packaging, preparing and deploying to Seldon Core can be found [here](https://apidocs.zenml.io/0.13.0/api_docs/integrations/#zenml.integrations.seldon.steps.seldon_deployer.seldon_model_deployer_step)