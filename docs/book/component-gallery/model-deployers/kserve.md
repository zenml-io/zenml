---
description: How to deploy models to Kubernetes with KServe
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The KServe Model Deployer is one of the available flavors of the[Model Deployer](./model-deployers.md) 
stack component. Provided with the MLflow and Seldon Core integration, it can 
be used to deploy and manage models on an inference server running on top of 
a Kubernetes cluster.

## When to use it?

[KServe](https://kserve.github.io/website) is a Kubernetes-based model inference 
platform built for highly scalable deployment use cases. It provides a 
standardized inference protocol across ML frameworks while supporting a 
serverless architecture with autoscaling including Scale to Zero on GPUs. KServe 
uses a simple and pluggable production serving architecture for production ML 
serving that includes prediction, pre-/post-processing, monitoring and 
explainability.

KServe encapsulates the complexity of autoscaling, networking, health checking,
and server configuration to bring cutting edge serving features like GPU 
Autoscaling, Scale to Zero, and Canary Rollouts to your ML deployments. 
It enables a simple, pluggable, and complete story for Production ML Serving 
including prediction, pre-processing, post-processing and explainability. 
KServe is being used across various organizations.

You should use the KServe Model Deployer:

* If you are looking to deploy your model with an advanced Model Inference 
Platform with Kubernetes, built for highly scalable use cases. 

* If you want to handle the lifecycle of the deployed model with no downtime, 
with possibility of scaling to zero on GPUs.

* Looking for out-of-the-box model serving runtimes that are easy to use 
and easy to deploy model from the majority of frameworks.

* If you want more advanced deployment strategies like A/B testing, 
canary deployments, ensembles and transformers.

* if you want to overcome the model deployment Scalability problems. Read more 
about KServe Multi Model Serving or [ModelMesh ](https://kserve.github.io/website/0.9/modelserving/mms/modelmesh/overview/).

If you are looking for a more easy way to deploy your models locally, you 
can use the [MLflow Model Deployer](./mlflow.md) flavor.

## How to deploy it?

ZenML provides a KServe flavor build on top of the KServe Integration to allow 
you to deploy and use your models in a production-grade environment. In order 
to use the integration you need to install it on your local machine to be able 
to register the KServe Model deployer with ZenML and add it to your stack:

```bash
zenml integration install kserve -y
```

To deploy and make use of the KServe integration we need to have the following 
prerequisites:

1. access to a Kubernetes cluster. The example accepts a `--kubernetes-context`
command line argument. This Kubernetes context needs to point to the Kubernetes
cluster where KServe model servers will be deployed. If the context is not
explicitly supplied to the example, it defaults to using the locally active
context.

2. KServe needs to be preinstalled and running in the target Kubernetes
cluster. Check out the [KServe Serverless installation Guide](https://kserve.github.io/website/0.9/admin/serverless/).

3. models deployed with KServe need to be stored in some form of
persistent shared storage that is accessible from the Kubernetes cluster where
KServe is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.).
You can use one of the supported [remote artifact store flavors](../artifact-stores/artifact-stores.md) 
to store your models as part of your stack. For a smoother experience running
KServe with a cloud artifact store, we also recommend configuring
explicit credentials for the artifact store. The KServe model deployer
knows how to automatically convert those credentials in the format needed
by KServe model servers to authenticate to the storage back-end where
models are stored.

Since the KServe Model Deployer is interacting with the KServe model serving 
Platform deployed on a Kubernetes cluster, you need to provide a set of 
configuration parameters. These parameters are:

* kubernetes_context: the Kubernetes context to use to contact the remote KServe
installation. If not specified, the current configuration is used. Depending 
on where the KServe model deployer is being used
* kubernetes_namespace: the Kubernetes namespace where the KServe deployment 
servers are provisioned and managed by ZenML. If not specified, the namespace 
set in the current configuration is used.
* base_url: the base URL of the Kubernetes ingress used to expose the 
KServe deployment servers.

{% hint style="info" %}
Configuring KServe in a Kubernetes cluster can be a complex and error-prone 
process, We provide a simple start guide on how to configure and setup KServe 
on your Kubernetes cluster, you can find it [here](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment#installing-kserve-eg-in-an-gke-cluster) 
we have also provided a set of Terraform-based recipes to quickly provision 
popular combinations of MLOps tools. More information about these recipes can 
be found in the [Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks)
{% endhint %}

### Managing KServe Authentication

The KServe Model Deployer requires access to the persistent storage where
models are located. In most cases, you will use the KServe model deployer
to serve models that are trained through ZenML pipelines and stored in the
ZenML Artifact Store, which implies that the KServe model deployer needs
to access the Artifact Store.

If KServe is already running in the same cloud as the Artifact Store (e.g.
S3 and an EKS cluster for AWS, or GCS and a GKE cluster for GCP), there are ways
of configuring cloud workloads to have implicit access to other cloud resources
like persistent storage without requiring explicit credentials.
However, if KServe is running in a different cloud, or on-prem, or if
implicit in-cloud workload authentication is not enabled, then you need to
configure explicit credentials for the Artifact Store to allow other components
like the KServe model deployer to authenticate to it. Every cloud Artifact
Store flavor supports some way of configuring explicit credentials and this is
documented for each individual flavor in the [Artifact Store documentation](../artifact-stores/artifact-stores.md).

When explicit credentials are configured in the Artifact Store, the KServe
Model Deployer doesn't need any additional configuration and will use those
credentials automatically to authenticate to the same persistent storage
service used by the Artifact Store. If the Artifact Store doesn't have
explicit credentials configured, then KServe will default to using
whatever implicit authentication method is available in the Kubernetes cluster
where it is running. For example, in AWS this means using the IAM role
attached to the EC2 or EKS worker nodes and in GCP this means using the
service account attached to the GKE worker nodes.

{% hint style="warning" %}
If the Artifact Store used in combination with the KServe Model Deployer
in the same ZenML stack does not have explicit credentials configured, then
the KServe Model Deployer might not be able to authenticate to the Artifact
Store which will cause the deployed model servers to fail.

To avoid this, we recommend that you use Artifact Stores with explicit
credentials in the same stack as the KServe Model Deployer. Alternatively,
if you're running KServe in one of the cloud providers, you should
configure implicit authentication for the Kubernetes nodes.
{% endhint %}

If you want to use a custom persistent storage with KServe, or if you
prefer to manually manage the authentication credentials attached to the
KServe model servers, you can use the approach described in the next
section.

#### Advanced: Configuring a Custom KServe Secret

The KServe model deployer stack component allows configuring an additional
`secret` attribute that can be used to specify custom credentials that KServe
should use to authenticate to the persistent storage service where models
are located. This is useful if you want to connect KServe to a persistent
storage service that is not supported as a ZenML Artifact Store, or if you don't
want to configure or use the same credentials configured for your Artifact
Store. The `secret` attribute must be set to the name of
[a ZenML secret](../../starter-guide/production-fundamentals/secrets-management.md)
containing credentials that will mounted as environment variables in the
KServe model servers.

{% hint style="info" %}
This method is not recommended, because it limits the KServe model deployer
to a single persistent storage service, whereas using the Artifact Store
credentials gives you more flexibility in combining the KServe model
deployer with any Artifact Store in the same ZenML stack.
{% endhint %}

KServe model servers use a proprietary format and very specific conventions
for credentials required for the supported persistent storage services and the
credentials that can be configured in the ZenML secret must also follow similar
conventions. This section covers a few common use cases and provides examples
of how to configure the ZenML secret to support them, but for more information
on supported configuration options, you can always refer to the
[KServe documentation for various providers](https://kserve.github.io/website/0.10/modelserving/storage/azure/azure/).

<details>
    <summary>KServe Authentication Secret Examples</summary>

Example of configuring a KServe secret for AWS S3: 

```shell
zenml secret create s3-kserve-secret \
--aws_access_key_id="<AWS-ACCESS-KEY-ID>" \ # AWS Access Key ID.
--aws_secret_access_key="<AWS-SECRET-ACCESS-KEY>" \ # AWS Secret Access Key.
--s3_region="<AWS_REGION>" \ # region to connect to.
--s3_endpoint="<S3_ENDPOINT>" \ # S3 API endpoint.
--s3_use_https="1" \ # set to 0 to disable https.
--s3_verify_ssl="1" \ # set to 0 to disable SSL certificate verification.
```

Example of configuring a KServe secret for GCS: 

```shell
zenml secret create gs-kserve-secret \
--google_application_credentials=@path/to/credentials.json \ # service account credentials JSON blob.
```

Example of configuring a KServe secret for Azure Blob Storage:

```shell
zenml secret create az-kserve-secret \
--azure_subscription_id="" \ # subscription ID of the service
# principal to use for authentication.
--azure_client_id="" \ # client ID of the service principal
# to use for authentication.
--azure_client_secret="" \ # client secret of the service
# principal to use for authentication.
--azure_tenant_id="" \ # tenant ID of the service principal
# to use for authentication.
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

>**Note**:
> If you chose to configure your own custom credentials to authenticate to the persistent storage service where models are stored, as covered in the [Advanced: Configuring a Custom KServe Secret](#advanced-configuring-a-custom-kserve-secret) section, you will need to specify a ZenML secret reference when you configure the KServe model deployer below:
> ```shell
>zenml model-deployer register kserve_deployer --flavor=kserve \
>  --kubernetes_context=<KUBERNETES-CONTEXT> \
>  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
>  --base_url=http://$INGRESS_HOST \
>  --secret=<ZENML_SECRET_NAME> 
> ```

```bash
zenml model-deployer register kserve_deployer --flavor=kserve \
  --kubernetes_context=<KUBERNETES-CONTEXT> \ 
  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
  --base_url=http://$INGRESS_HOST \
```

We can now use the model deployer in our stack.

```
zenml stack update kserve_stack --model-deployer=kserve_deployer
```

As the packaging and preparation of the model artifacts to the right format 
can be a bit of a challenge, ZenML's KServe Integration comes with a built-in 
model deployment step that can be used to deploy your models with the minimum 
of effort.

This step will:
* Verify if the model is already deployed in the KServe cluster. If not, it 
will deploy the model.
* Prepare the model artifacts to the right format for the TF, MLServer runtimes 
servers.
* Package, verify and prepare the model artifact for the PyTorch runtime server 
since it requires additional files.
* Upload the model artifacts to the Artifact Store.

An example of how to use the model deployment step is shown below.

```python
from zenml.integrations.kserve.services import KServeDeploymentConfig
from zenml.integrations.kserve.steps import (
    KServeDeployerStepParameters,
    TorchServeParameters,
    kserve_model_deployer_step,
)

MODEL_NAME = "mnist-pytorch"

pytorch_model_deployer = kserve_model_deployer_step(
    params=KServeDeployerStepParameters(
        service_config=KServeDeploymentConfig(
            model_name=MODEL_NAME,
            replicas=1,
            predictor="pytorch",
            resources={"requests": {"cpu": "200m", "memory": "500m"}},
        ),
        timeout=120,
        torch_serve_parameters=TorchServeParameters(
            model_class="steps/pytorch_steps/mnist.py",
            handler="steps/pytorch_steps/mnist_handler.py",
        ),
    )
)
```

Within the `KServeDeploymentConfig` you can configure:
   * `model_name`: the name of the model in the KServe cluster and in ZenML.
   * `replicas`: the number of replicas with which to deploy the model
   * `predictor`: the type of predictor to use for the model. The
    predictor type can be one of the following: `tensorflow`, `pytorch`, `sklearn`, `xgboost`, `custom`.
   * `resources`: This can be configured by passing a dictionary with the
    `requests` and `limits` keys. The values for these keys can be a dictionary
    with the `cpu` and `memory` keys. The values for these keys can be a string
    with the amount of CPU and memory to be allocated to the model.


A concrete example of using the KServe Model Deployer can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment).

For more information and a full list of configurable attributes of the KServe 
Model Deployer, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kserve/#zenml.integrations.kserve.model_deployers).

{% hint style="info" %}
The model deployment step are experimental good for standard use cases. 
However, if you need to customize the deployment step, you can always create 
your own model deployment step. Find more information about model deployment 
steps in the [Model Deployment Steps](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kserve/#zenml.integrations.kserve.steps) section.
{% endhint %}

## Custom Model Deployment

While KServe is a good fit for most use cases with the built-in model servers, 
it is not always the best fit for your custom model deployment use case. For
that reason KServe allows you to create your own model server using the KServe 
`ModelServer` API where you can customize the predict, the pre- and 
post-processing functions. With ZenML's KServe Integration, you can create 
your own custom model deployment code by creating a custom predict function 
that will be passed to a custom deployment step responsible for preparing a 
Docker image for the model server.

This `custom_predict` function should be getting the model and the input data 
as arguments and returns the output data. ZenML will take care of loading 
the model into memory, starting the KServe `ModelServer` that will be 
responsible for serving the model, and running the predict function.

```python
def pre_process(tensor: torch.Tensor) -> dict:
    """Pre process the data to be used for prediction."""
    pass


def post_process(prediction: torch.Tensor) -> str:
    """Pre process the data"""
    pass


def custom_predict(
    model: Any,
    request: dict,
) -> dict:
    """Custom Prediction function.

    The custom predict function is the core of the custom deployment. The function
    is called by the custom deployment class defined for the serving tool.
    The current implementation requires the function to get the model loaded in the memory and
    a request with the data to predict.

    Args:
        model (Any): The model to use for prediction.
        request: The prediction response of the model is an array-like object.
    Returns:
        The prediction in an array-like format (e.g. np.ndarray, List[Any], str, bytes, Dict[str, Any])
    """
    pass
```

Then this custom predict function `path` can be passed to the custom 
deployment parameters.

```python
from zenml.integrations.kserve.steps import (
    kserve_custom_model_deployer_step,
    KServeDeployerStepParameters, 
    CustomDeployParameters
)
from zenml.integrations.kserve.services.kserve_deployment import (
    KServeDeploymentConfig
)

kserve_pytorch_custom_deployment = kserve_custom_model_deployer_step(
    params=KServeDeployerStepParameters(
        service_config=KServeDeploymentConfig(
            model_name="kserve-pytorch-custom-model",
            replicas=1,
            predictor="custom",
            resources={"requests": {"cpu": "200m", "memory": "500m"}},
        ),
        timeout=240,
        custom_deploy_parameters=CustomDeployParameters(
            predict_function="kserve_pytorch.steps.pytorch_custom_deploy_code.custom_predict"
        ),
    )
)
```
The full code example can be found [here](https://github.com/zenml-io/zenml/blob/main/examples/custom_code_deployment/).

### Advanced Custom Code Deployment with KServe Integration

{% hint style="warning" %}
Before creating your custom model class, you should take a look at the
['Deploy Custom Python Model Server with InferenceService'](https://kserve.github.io/website/0.9/modelserving/v1beta1/custom/custom_model/) section of the KServe documentation.
{% endhint %}

The built-in KServe custom deployment step is a good starting point for
deploying your custom models. However, if you want to deploy more than the
trained model, you can create your own Custom Model Class and a custom step to 
achieve this.

Example of the [custom model class](https://apidocs.zenml.io/0.13.0/api_docs/integrations/#zenml.integrations.kserve.custom_deployer.zenml_custom_model.ZenMLCustomModel)

The built-in KServe custom deployment step responsible for packaging, preparing 
and deploying to KServe can be found [here](https://apidocs.zenml.io/0.13.0/api_docs/integrations/#zenml.integrations.kserve.steps.kserve_deployer.kserve_model_deployer_step)