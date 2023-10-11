---
description: How to deploy models to Kubernetes with Seldon Core
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The Seldon Core Model Deployer is one of the available flavors of the 
[Model Deployer](./model-deployers.md) stack component. Provided with the 
MLflow integration it can be used to deploy and manage models on an inference 
server running on top of a Kubernetes cluster.

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

* If you want to handle the lifecycle of the deployed model with no downtime, 
including updating the runtime graph, scaling, monitoring, and security.

* Looking for more advanced API endpoints to interact with the deployed model, 
including REST and GRPC endpoints.

* If you want more advanced deployment strategies like A/B testing, canary 
deployments, and more.

* if you have a need for a more complex deployment process which can be 
customized by the advanced inference graph that includes custom 
[TRANSFORMER](https://docs.seldon.io/projects/seldon-core/en/latest/workflow/overview.html) 
and [ROUTER](https://docs.seldon.io/projects/seldon-core/en/latest/analytics/routers.html?highlight=routers#).

If you are looking for a more easy way to deploy your models locally, you can 
use the [MLflow Model Deployer](./mlflow.md) flavor.

## How to deploy it?

ZenML provides a Seldon Core flavor build on top of the Seldon Core Integration 
to allow you to deploy and use your models in a production-grade environment. 
In order to use the integration you need to install it on your local machine to 
be able to register a Seldon Core Model deployer with ZenML and add it to your 
stack:

```bash
zenml integration install seldon -y
```

To deploy and make use of the Seldon Core integration we need to have the 
following prerequisites:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where Seldon Core model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context. 

2. Seldon Core needs to be preinstalled and running in the target Kubernetes
cluster. Check out the [official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup).

3. models deployed with Seldon Core need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
Seldon Core is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).
You can use one of the supported [remote storage flavors](../artifact-stores/artifact-stores.md) 
to store your models as part of your stack.

Since the Seldon Model Deployer is interacting with the Seldon Core model 
server deployed on a Kubernetes cluster, you need to provide a set of 
configuration parameters. These parameters are:

* kubernetes_context: the Kubernetes context to use to contact the remote 
Seldon Core installation. If not specified, the current configuration is used. 
Depending on where the Seldon model deployer is being used
* kubernetes_namespace: the Kubernetes namespace where the Seldon Core 
deployment servers are provisioned and managed by ZenML. If not specified, 
the namespace set in the current configuration is used.
* base_url: the base URL of the Kubernetes ingress used to expose the Seldon 
Core deployment servers.
* secret: the name of a ZenML secret containing the credentials used by 
Seldon Core storage initializers to authenticate to the Artifact Store in the
ZenML stack. The secret must be registered using the `zenml secrets-manager
secret register` command. The secret schema must be one of the built-in
schemas provided by the Seldon Core integration: `seldon_s3` for AWS S3,
`seldon_gs` for GCS, and `seldon_az` for Azure. 
* kubernetes_secret_name: the name of the Kubernetes secret that will be
created to store the Seldon Core credentials. If not specified, the secret name
will be derived from the ZenML secret name.



{% hint style="info" %}
Configuring a Seldon Core in a Kubernetes cluster can be a complex and 
error-prone process, so we have provided a set of Terraform-based recipes to 
quickly provision popular combinations of MLOps tools. More information about 
these recipes can be found in the [Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks).
{% endhint %}

### Managing Seldon Core Credentials

#### Seldon Core Secret using ZenML Secrets Manager

The Seldon Core model servers need to retrieve model artifacts from the Artifact
Store in the ZenML stack. This requires passing authentication credentials to 
the Seldon Core servers. To facilitate this, a ZenML secret must be created with
the proper credentials and specified when registering the Seldon Core Model 
Deployer component using the --secret argument in the CLI command. To complete
the configuration, the s3-store ZenML secret must be set as a Seldon Model
Deployer configuration attribute.

Built-in secret schemas are provided by the Seldon Core integration for 
the 3 main supported Artifact Stores: S3, GCS, and Azure. The secret schemas 
are `seldon_s3` for AWS S3, `seldon_gs` for GCS, and `seldon_az` for Azure. For
more information on secrets, secret schemas, and their usage in ZenML, refer to 
the [Secrets Manager](../secrets-managers/secrets-managers.md) documentation.

<details>
    <summary>ZenML Seldon Deployer Storage Secrets </summary>

```shell
# Example of a Seldon Core secret for GCS
zenml secrets-manager secret register -s seldon_gs gs-seldon-secret \
--rclone_config_gs_client_secret="" \  #OAuth client secret. 
--rclone_config_gs_token="" \ # OAuth Access Token as a JSON blob.
--rclone_config_gs_project_number="" \ # project number.
--rclone_config_gs_service_account_credentials="" \ #service account credentials JSON blob.
--rclone_config_gs_anonymous="" \ # Access public buckets and objects without credentials. 
# Set to True if you just want to download files and don't configure credentials.
--rclone_config_gs_auth_url="" \ # auth server URL.

# Example of a Seldon Core secret for AWS S3 
zenml secrets-manager secret register -s seldon_s3 s3-seldon-secret \
--rclone_config_s3_provider="" \ # the S3 provider (e.g. aws, ceph, minio).
--rclone_config_s3_env_auth="" \ # get AWS credentials from EC2/ECS meta data
# (i.e. with IAM roles configuration). Only applies if access_key_id and secret_access_key are blank.
--rclone_config_s3_access_key_id="" \ # AWS Access Key ID.
--rclone_config_s3_secret_access_key="" \ # AWS Secret Access Key.
--rclone_config_s3_session_token="" \ # AWS Session Token.
--rclone_config_s3_region="" \ # region to connect to.
--rclone_config_s3_endpoint="" \ # S3 API endpoint.

# Example of a Seldon Core secret for Azure Blob Storage
zenml secrets-manager secret register -s seldon_az az-seldon-secret \
--rclone_config_azureblob_account="" \ # storage Account Name. Leave blank to
# use SAS URL or MSI.
--rclone_config_azureblob_key="" \ # storage Account Key. Leave blank to
# use SAS URL or MSI.
--rclone_config_azureblob_sas_url="" \ # SAS URL for container level access
# only. Leave blank if using account/key or MSI.
--rclone_config_azureblob_use_msi="" \ # use a managed service identity to
# authenticate (only works in Azure).
```
</details>

#### Seldon Core Secret using Kubernetes Secrets

Alternatively, you can create a Kubernetes secret containing the credentials
required by Seldon Core to access the Artifact Store. The secret must be
created in the same namespace where the Seldon Core model servers are deployed.

Each of the supported Artifact Stores has a different set of required
credentials. For more information on the required credentials, refer to the
Rclone documentation for the [S3](https://rclone.org/s3/), 
[GCS](https://rclone.org/googlecloudstorage/), 
and [Azure](https://rclone.org/azureblob/) backends.

The following example shows how to create a Kubernetes secret for Minio which
is an S3-compatible object storage server.

<details>
    <summary>Kubernetes Secret for Seldon to Access Minio </summary>

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: minio-seldon-secret
  namespace: zenml-workloads
  labels:
    app: "zenml"
data:
  RCLONE_CONFIG_S3_ACCESS_KEY_ID: "S3_ACCESS_KEY_ID"
  RCLONE_CONFIG_S3_ENDPOINT: "http://mini-service:9000"
  RCLONE_CONFIG_S3_PROVIDER: "Minio"
  RCLONE_CONFIG_S3_ENV_PATH: "false"
  RCLONE_CONFIG_S3_SECRET_ACCESS_KEY: "S3_SECRET_ACCESS_KEY"
  RCLONE_CONFIG_S3_TYPE: "s3"
type: Opaque
```

Once the secret is created, it can be referenced in the Seldon Core Model
Deployer configuration using the `kubernetes_secret_name` attribute when 
registering the deployer component.

```bash
# Create the secret
kubectl apply -f minio-seldon-secret.yaml

# Register the Seldon Core Model Deployer
zenml model-deployer register seldon_deployer --flavor=seldon \
  --kubernetes_context=zenml-eks \
  --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST \
  --kubernetes_secret_name=minio-seldon-secret 
```
</details>

## How do you use it?

For registering the model deployer, we need the URL of the Istio Ingress Gateway deployed on the Kubernetes cluster. We can get this URL by running the following command (assuming that the service name is `istio-ingressgateway`, deployed in the `istio-system` namespace):

```bash
# For GKE clusters, the host is the GKE cluster IP address.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
# For EKS clusters, the host is the EKS cluster IP hostname.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Now register the model deployer:

```bash
# Register the Seldon Core Model Deployer with secret registred in ZenML
zenml model-deployer register seldon_deployer --flavor=seldon \
  --kubernetes_context=zenml-eks \
  --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST \
  --secret=s3-store-credentials 

# Register the Seldon Core Model Deployer with secret created in Kubernetes
zenml model-deployer register seldon_deployer --flavor=seldon \
    --kubernetes_context=zenml-eks \
    --kubernetes_namespace=zenml-workloads \
    --base_url=http://$INGRESS_HOST \
    --kubernetes_secret_name=s3-seldon-secret
```

We can now use the model deployer in our stack.

```bash
zenml stack update seldon_stack --model-deployer=seldon_deployer
```

The following code snippet shows how to use the Seldon Core Model Deployer to 
deploy a model inside a ZenML pipeline step:

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

Within the `SeldonDeploymentConfig` you can configure:
   * `model_name`: the name of the model in the KServe cluster and in ZenML.
   * `replicas`: the number of replicas with which to deploy the model
   * `implementation`: the type of Seldon inference server to use for the model. The
    implementation type can be one of the following: `TENSORFLOW_SERVER`, 
    `SKLEARN_SERVER`, `XGBOOST_SERVER`, `custom`.
   * `parameters`: an optional list of parameters (`SeldonDeploymentPredictorParameter`) 
    to pass to the deployment predictor in a form of:
     * `name`
     * `type`
     * `value`
   * `resources`: the resources to be allocated to the model. This can be 
    configured by passing a `SeldonResourceRequirements` object with the `requests` and `limits` properties. 
    The values for these properties can be a dictionary with the `cpu` and `memory` 
    keys. The values for these keys can be a string with the amount of CPU and 
    memory to be allocated to the model.

A concrete example of using the Seldon Core Model Deployer can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/seldon_deployment).

For more information and a full list of configurable attributes of the Seldon 
Core Model Deployer, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-seldon/#zenml.integrations.seldon.model_deployers).

## Custom Model Deployment

When you have a custom use-case where Seldon Core pre-packaged inference 
servers cannot cover your needs, you can leverage the language wrappers to 
containerise your machine learning model(s) and logic.
With ZenML's Seldon Core Integration, you can create your own custom model
deployment code by creating a custom predict function that will be passed
to a custom deployment step responsible for preparing a Docker image for the
model server.

This `custom_predict` function should be getting the model and the input data 
as arguments and return the output data. ZenML will take care of loading the 
model into memory, starting the `seldon-core-microservice` that will be 
responsible for serving the model, and running the predict function.

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

    The custom predict function is the core of the custom deployment, the 
    function is called by the custom deployment class defined for the serving 
    tool. The current implementation requires the function to get the model 
    loaded in the memory and a request with the data to predict.

    Args:
        model (Any): The model to use for prediction.
        request: The prediction response of the model is an array-like format.
    Returns:
        The prediction in an array-like format. (e.g: np.ndarray, 
        List[Any], str, bytes, Dict[str, Any])
    """
    pass
```

Then this custom predict function `path` can be passed to the custom deployment 
parameters.

```python
from zenml.integrations.seldon.steps import (
  seldon_custom_model_deployer_step, 
    SeldonDeployerStepParameters,
    CustomDeployParameters,
)
from zenml.integrations.seldon.services import SeldonDeploymentConfig

seldon_tensorflow_custom_deployment = seldon_custom_model_deployer_step(
    config=SeldonDeployerStepParameters(
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
deploying your custom models. However, if you want to deploy more than the
trained model, you can create your own Custom Class and a custom step
to achieve this.

Example of the [custom class](https://apidocs.zenml.io/0.13.0/api_docs/integrations/#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel).

The built-in Seldon Core custom deployment step responsible for packaging, 
preparing and deploying to Seldon Core can be found [here](https://apidocs.zenml.io/latest/integration_code_docs/integrations-seldon/#zenml.integrations.seldon.steps.seldon_deployer.seldon_model_deployer_step).
