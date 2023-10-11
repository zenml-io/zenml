---
description: How to deploy models to Kubernetes with KServe
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The KServe Model Deployer is one of the available flavors of the[Model Deployer](./model-deployers.md) 
stack component. Provided with the MLflow and Seldon Core integration it can 
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
You can use one of the supported [remote storage flavors](../artifact-stores/artifact-stores.md) 
to store your models as part of your stack

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
* secret: the name of a ZenML secret containing the credentials used by KServe 
storage initializers to authenticate to the Artifact Store


{% hint style="info" %}
Configuring KServe in a Kubernetes cluster can be a complex and error-prone 
process, We provide a simple start guide on how to configure and setup KServe 
on your Kubernetes cluster, you can find it [here](https://github.com/zenml-io/zenml/tree/main/examples/kserve_deployment#installing-kserve-eg-in-an-gke-cluster) 
we have also provided a set of Terraform-based recipes to quickly provision 
popular combinations of MLOps tools. More information about these recipes can 
be found in the [Open Source MLOps Stack Recipes](https://github.com/zenml-io/mlops-stacks)
{% endhint %}

### Managing KServe Credentials

The KServe model servers need to access the Artifact Store in the ZenML
stack to retrieve the model artifacts. This usually involve passing some
credentials to the KServe model servers required to authenticate with
the Artifact Store. In ZenML, this is done by creating a ZenML secret with the
proper credentials and configuring the KServe Model Deployer stack component
to use it, by passing the `--secret` argument to the CLI command used
to register the model deployer. We've already done the latter, now all that is
left to do is to configure the `s3-store` ZenML secret specified before as a
KServe Model Deployer configuration attribute with the credentials needed by
KServe to access the artifact store.

There are built-in secret schemas that the KServe integration provides which
can be used to configure credentials for the 3 main types of Artifact Stores
supported by ZenML: S3, GCS and Azure.

you can use `kserve_s3` for AWS S3 or `kserve_gs` for GCS and `kserve_az` for 
Azure. To read more about secrets, secret schemas and how they are used in 
ZenML, please refer to the [Secrets Manager](../secrets-managers/secrets-managers.md).

{% hint style="warning" %}
The recommended way to pass the credentials to the KServe model deployer is to 
use a file that contains the credentials. You can achieve this by adding the 
`@` followed by the path to the file to the `--credentials` argument.
(e.g. `--credentials @/path/to/credentials.json`)
{% endhint %}

The following is an example of registering an GS secret with the KServe model 
deployer:

```bash
$ zenml secrets-manager secret register -s kserve_gs kserve_secret \
    --namespace="zenml-workloads" \
    --credentials="@~/sa-deployment-temp.json" \

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃             SECRET_KEY             │ SECRET_VALUE ┃
┠────────────────────────────────────┼──────────────┨
┃            storage_type            │ ***          ┃
┃              namespace             │ ***          ┃
┃             credentials            │ ***          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛
```

```bash
$ zenml secrets-manager secret get kserve_secret
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃    SECRET_KEY    │ SECRET_VALUE              ┃
┠──────────────────┼───────────────────────────┨
┃   storage_type   │ GCS                       ┃
┠──────────────────┼───────────────────────────┨
┃    namespace     │ kserve-test               ┃
┠──────────────────┼───────────────────────────┨
┃   credentials    │ ~/sa-deployment-temp.json ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

For more information and a full list of configurable attributes of the KServe 
secret schemas, check out the [API Docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-kserve/#zenml.integrations.kserve.secret_schemas).

## How do you use it?

We can register the model deployer and use it in our active stack:

```bash
zenml model-deployer register kserve_gke --flavor=kserve \
  --kubernetes_context=gke_zenml-core_us-east1-b_zenml-test-cluster \ 
  --kubernetes_namespace=zenml-workloads \
  --base_url=$INGRESS_URL \
  --secret=kserve_secret

# Now we can use the model deployer in our stack
zenml stack update kserve_stack --model-deployer=kserve_gke
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
ModelServer API where you can customize the predict, the pre- and 
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