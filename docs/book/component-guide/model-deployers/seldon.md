---
description: Deploying models to Kubernetes with Seldon Core.
---

# Seldon

[Seldon Core](https://github.com/SeldonIO/seldon-core) is a production grade source-available model serving platform. It packs a wide range of features built around deploying models to REST/GRPC microservices that include monitoring and logging, model explainers, outlier detectors and various continuous deployment strategies such as A/B testing, canary deployments and more.

Seldon Core also comes equipped with a set of built-in model server implementations designed to work with standard formats for packaging ML models that greatly simplify the process of serving models for real-time inference.

{% hint style="warning" %}
The Seldon Core model deployer integration is currently not supported under **MacOS**.
{% endhint %}

## When to use it?

[Seldon Core](https://github.com/SeldonIO/seldon-core) is a production-grade source-available model serving platform. It packs a wide range of features built around deploying models to REST/GRPC microservices that include monitoring and logging, model explainers, outlier detectors, and various continuous deployment strategies such as A/B testing, canary deployments, and more.

Seldon Core also comes equipped with a set of built-in model server implementations designed to work with standard formats for packaging ML models that greatly simplify the process of serving models for real-time inference.

You should use the Seldon Core Model Deployer:

* If you are looking to deploy your model on a more advanced infrastructure like Kubernetes.
* If you want to handle the lifecycle of the deployed model with no downtime, including updating the runtime graph, scaling, monitoring, and security.
* Looking for more advanced API endpoints to interact with the deployed model, including REST and GRPC endpoints.
* If you want more advanced deployment strategies like A/B testing, canary deployments, and more.
* if you have a need for a more complex deployment process that can be customized by the advanced inference graph that includes custom [TRANSFORMER](https://docs.seldon.io/projects/seldon-core/en/latest/workflow/overview.html) and [ROUTER](https://docs.seldon.io/projects/seldon-core/en/latest/analytics/routers.html?highlight=routers).

If you are looking for a more easy way to deploy your models locally, you can use the [MLflow Model Deployer](mlflow.md) flavor.

## How to deploy it?

ZenML provides a Seldon Core flavor build on top of the Seldon Core Integration to allow you to deploy and use your models in a production-grade environment. In order to use the integration you need to install it on your local machine to be able to register a Seldon Core Model deployer with ZenML and add it to your stack:

```bash
zenml integration install seldon -y
```

To deploy and make use of the Seldon Core integration we need to have the following prerequisites:

1. access to a Kubernetes cluster. This can be configured using the `kubernetes_context` configuration attribute to point to a local `kubectl` context or an in-cluster configuration, but the recommended approach is to [use a Service Connector](seldon.md#using-a-service-connector) to link the Seldon Deployer Stack Component to a Kubernetes cluster.
2. Seldon Core needs to be preinstalled and running in the target Kubernetes cluster. Check out the [official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup) or the [EKS installation example below](seldon.md#installing-seldon-core-eg-in-an-eks-cluster).
3. models deployed with Seldon Core need to be stored in some form of persistent shared storage that is accessible from the Kubernetes cluster where Seldon Core is installed (e.g. AWS S3, GCS, Azure Blob Storage, etc.). You can use one of the supported [remote artifact store flavors](../artifact-stores/artifact-stores.md) to store your models as part of your stack. For a smoother experience running Seldon Core with a cloud artifact store, we also recommend configuring explicit credentials for the artifact store. The Seldon Core model deployer knows how to automatically convert those credentials in the format needed by Seldon Core model servers to authenticate to the storage back-end where models are stored.

Since the Seldon Model Deployer is interacting with the Seldon Core model server deployed on a Kubernetes cluster, you need to provide a set of configuration parameters. These parameters are:

* kubernetes\_context: the Kubernetes context to use to contact the remote Seldon Core installation. If not specified, the active Kubernetes context is used or the in-cluster configuration is used if the model deployer is running in a Kubernetes cluster. The recommended approach is to [use a Service Connector](seldon.md#using-a-service-connector) to link the Seldon Deployer Stack Component to a Kubernetes cluster and to skip this parameter.
* kubernetes\_namespace: the Kubernetes namespace where the Seldon Core deployment servers are provisioned and managed by ZenML. If not specified, the namespace set in the current configuration is used.
* base\_url: the base URL of the Kubernetes ingress used to expose the Seldon Core deployment servers.

In addition to these parameters, the Seldon Core Model Deployer may also require additional configuration to be set up to allow it to authenticate to the remote artifact store or persistent storage service where model artifacts are located. This is covered in the [Managing Seldon Core Authentication](seldon.md#managing-seldon-core-authentication) section.

### Seldon Core Installation Example

The following example briefly shows how you can install Seldon in an EKS Kubernetes cluster. It assumes that the EKS cluster itself is already set up and configured with IAM access. For more information or tutorials for other clouds, check out the [official Seldon Core installation instructions](https://github.com/SeldonIO/seldon-core/tree/master/examples/auth#demo-setup).

1. Configure EKS cluster access locally, e.g:

```bash
aws eks --region us-east-1 update-kubeconfig --name zenml-cluster --alias zenml-eks
```

2. Install Istio 1.5.0 (required for the latest Seldon Core version):

```bash
curl -L [https://istio.io/downloadIstio](https://istio.io/downloadIstio) | ISTIO_VERSION=1.5.0 sh -
cd istio-1.5.0/
bin/istioctl manifest apply --set profile=demo
```

3. Set up an Istio gateway for Seldon Core:

```bash
curl https://raw.githubusercontent.com/SeldonIO/seldon-core/master/notebooks/resources/seldon-gateway.yaml | kubectl apply -f -
```

4. Install Seldon Core:

```bash
helm install seldon-core seldon-core-operator \
    --repo https://storage.googleapis.com/seldon-charts \
    --set usageMetrics.enabled=true \
    --set istio.enabled=true \
    --namespace seldon-system
```

5. Test that the installation is functional

```bash
kubectl apply -f iris.yaml
```

with `iris.yaml` defined as follows:

```yaml
apiVersion: machinelearning.seldon.io/v1
kind: SeldonDeployment
metadata:
  name: iris-model
  namespace: default
spec:
  name: iris
  predictors:
  - graph:
      implementation: SKLEARN_SERVER
      modelUri: gs://seldon-models/v1.14.0-dev/sklearn/iris
      name: classifier
    name: default
    replicas: 1
```

Then extract the URL where the model server exposes its prediction API:

```bash
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

And use curl to send a test prediction API request to the server:

```bash
curl -X POST http://$INGRESS_HOST/seldon/default/iris-model/api/v1.0/predictions \
         -H 'Content-Type: application/json' \
         -d '{ "data": { "ndarray": [[1,2,3,4]] } }'
```

### Using a Service Connector

To set up the Seldon Core Model Deployer to authenticate to a remote Kubernetes cluster, it is recommended to leverage the many features provided by [the Service Connectors](../../how-to/infrastructure-deployment/auth-management/README.md) such as auto-configuration, local client login, best security practices regarding long-lived credentials and fine-grained access control and reusing the same credentials across multiple stack components.

Depending on where your target Kubernetes cluster is running, you can use one of the following Service Connectors:

* [the AWS Service Connector](../../how-to/infrastructure-deployment/auth-management/aws-service-connector.md), if you are using an AWS EKS cluster.
* [the GCP Service Connector](../../how-to/infrastructure-deployment/auth-management/gcp-service-connector.md), if you are using a GKE cluster.
* [the Azure Service Connector](../../how-to/infrastructure-deployment/auth-management/azure-service-connector.md), if you are using an AKS cluster.
* [the generic Kubernetes Service Connector](../../how-to/infrastructure-deployment/auth-management/kubernetes-service-connector.md) for any other Kubernetes cluster.

If you don't already have a Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure a Service Connector that can be used to access more than one Kubernetes cluster or even more than one type of cloud resource:

```sh
zenml service-connector register -i
```

A non-interactive CLI example that leverages [the AWS CLI configuration](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) on your local machine to auto-configure an AWS Service Connector targeting a single EKS cluster is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type aws --resource-type kubernetes-cluster --resource-name <EKS_CLUSTER_NAME> --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register eks-zenhacks --type aws --resource-type kubernetes-cluster --resource-id zenhacks-cluster --auto-configure
⠼ Registering service connector 'eks-zenhacks'...
Successfully registered service connector `eks-zenhacks` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES   ┃
┠───────────────────────┼──────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Alternatively, you can configure a Service Connector through the ZenML dashboard:

![AWS Service Connector Type](../../.gitbook/assets/aws-service-connector-type.png) ![AWS EKS Service Connector Configuration](../../.gitbook/assets/aws-eks-service-connector-configuration.png)

> **Note**: Please remember to grant the entity associated with your cloud credentials permissions to access the Kubernetes cluster and to list accessible Kubernetes clusters. For a full list of permissions required to use a AWS Service Connector to access one or more Kubernetes cluster, please refer to the [documentation for your Service Connector of choice](../../how-to/infrastructure-deployment/auth-management/README.md) or read the documentation available in the interactive CLI commands and dashboard. The Service Connectors supports many different authentication methods with different levels of security and convenience. You should pick the one that best fits your use-case.

If you already have one or more Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the Kubernetes cluster that you want to use for your Seldon Core Model Deployer by running e.g.:

```sh
zenml service-connector list-resources --resource-type kubernetes-cluster
```

{% code title="Example Command Output" %}
```
The following 'kubernetes-cluster' resources can be accessed by service connectors that you have configured:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES                                ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────┨
┃ bdf1dc76-e36b-4ab4-b5a6-5a9afea4822f │ eks-zenhacks   │ 🔶 aws         │ 🌀 kubernetes-cluster │ zenhacks-cluster                              ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────┨
┃ b57f5f5c-0378-434c-8d50-34b492486f30 │ gcp-multi      │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster                            ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼───────────────────────────────────────────────┨
┃ d6fc6004-eb76-4fd7-8fa1-ec600cced680 │ azure-multi    │ 🇦 azure       │ 🌀 kubernetes-cluster │ demo-zenml-demos/demo-zenml-terraform-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on a Service Connector to use to connect to the target Kubernetes cluster where Seldon Core is installed, you can register the Seldon Core Model Deployer as follows:

```sh
# Register the Seldon Core Model Deployer
zenml model-deployer register <MODEL_DEPLOYER_NAME> --flavor=seldon \
  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
  --base_url=http://$INGRESS_HOST

# Connect the Seldon Core Model Deployer to the target cluster via a Service Connector
zenml model-deployer connect <MODEL_DEPLOYER_NAME> -i
```

A non-interactive version that connects the Seldon Core Model Deployer to a target Kubernetes cluster through a Service Connector:

```sh
zenml model-deployer connect <MODEL_DEPLOYER_NAME> --connector <CONNECTOR_ID> --resource-id <CLUSTER_NAME>
```

{% code title="Example Command Output" %}
```
$ zenml model-deployer connect seldon-test --connector gcp-multi --resource-id zenml-test-cluster
Successfully connected model deployer `seldon-test` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES     ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────────┨
┃ b57f5f5c-0378-434c-8d50-34b492486f30 │ gcp-multi      │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛
```
{% endcode %}

A similar experience is available when you configure the Seldon Core Model Deployer through the ZenML dashboard:

![Seldon Core Model Deployer Configuration](../../.gitbook/assets/seldon-model-deployer-service-connector.png)

### Managing Seldon Core Authentication

The Seldon Core Model Deployer requires access to the persistent storage where models are located. In most cases, you will use the Seldon Core model deployer to serve models that are trained through ZenML pipelines and stored in the ZenML Artifact Store, which implies that the Seldon Core model deployer needs to access the Artifact Store.

If Seldon Core is already running in the same cloud as the Artifact Store (e.g. S3 and an EKS cluster for AWS, or GCS and a GKE cluster for GCP), there are ways of configuring cloud workloads to have implicit access to other cloud resources like persistent storage without requiring explicit credentials. However, if Seldon Core is running in a different cloud, or on-prem, or if implicit in-cloud workload authentication is not enabled, then you need to configure explicit credentials for the Artifact Store to allow other components like the Seldon Core model deployer to authenticate to it. Every cloud Artifact Store flavor supports some way of configuring explicit credentials and this is documented for each individual flavor in the [Artifact Store documentation](../artifact-stores/artifact-stores.md).

When explicit credentials are configured in the Artifact Store, the Seldon Core Model Deployer doesn't need any additional configuration and will use those credentials automatically to authenticate to the same persistent storage service used by the Artifact Store. If the Artifact Store doesn't have explicit credentials configured, then Seldon Core will default to using whatever implicit authentication method is available in the Kubernetes cluster where it is running. For example, in AWS this means using the IAM role attached to the EC2 or EKS worker nodes, and in GCP this means using the service account attached to the GKE worker nodes.

{% hint style="warning" %}
If the Artifact Store used in combination with the Seldon Core Model Deployer in the same ZenML stack does not have explicit credentials configured, then the Seldon Core Model Deployer might not be able to authenticate to the Artifact Store which will cause the deployed model servers to fail.

To avoid this, we recommend that you use Artifact Stores with explicit credentials in the same stack as the Seldon Core Model Deployer. Alternatively, if you're running Seldon Core in one of the cloud providers, you should configure implicit authentication for the Kubernetes nodes.
{% endhint %}

If you want to use a custom persistent storage with Seldon Core, or if you prefer to manually manage the authentication credentials attached to the Seldon Core model servers, you can use the approach described in the next section.

**Advanced: Configuring a Custom Seldon Core Secret**

The Seldon Core model deployer stack component allows configuring an additional `secret` attribute that can be used to specify custom credentials that Seldon Core should use to authenticate to the persistent storage service where models are located. This is useful if you want to connect Seldon Core to a persistent storage service that is not supported as a ZenML Artifact Store, or if you don't want to configure or use the same credentials configured for your Artifact Store. The `secret` attribute must be set to the name of [a ZenML secret](../../how-to/project-setup-and-management/interact-with-secrets.md) containing credentials configured in the format supported by Seldon Core.

{% hint style="info" %}
This method is not recommended, because it limits the Seldon Core model deployer to a single persistent storage service, whereas using the Artifact Store credentials gives you more flexibility in combining the Seldon Core model deployer with any Artifact Store in the same ZenML stack.
{% endhint %}

Seldon Core model servers use [`rclone`](https://rclone.org/) to connect to persistent storage services and the credentials that can be configured in the ZenML secret must also be in the configuration format supported by `rclone`. This section covers a few common use cases and provides examples of how to configure the ZenML secret to support them, but for more information on supported configuration options, you can always refer to the [`rclone` documentation for various providers](https://rclone.org/).

<details>

<summary>Seldon Core Authentication Secret Examples</summary>

Example of configuring a Seldon Core secret for AWS S3:

```shell
zenml secret create s3-seldon-secret \
--rclone_config_s3_type="s3" \ # set to 's3' for S3 storage.
--rclone_config_s3_provider="aws" \ # the S3 provider (e.g. aws, Ceph, Minio).
--rclone_config_s3_env_auth=False \ # set to true to use implicit AWS authentication from EC2/ECS meta data
# (i.e. with IAM roles configuration). Only applies if access_key_id and secret_access_key are blank.
--rclone_config_s3_access_key_id="<AWS-ACCESS-KEY-ID>" \ # AWS Access Key ID.
--rclone_config_s3_secret_access_key="<AWS-SECRET-ACCESS-KEY>" \ # AWS Secret Access Key.
--rclone_config_s3_session_token="" \ # AWS Session Token.
--rclone_config_s3_region="" \ # region to connect to.
--rclone_config_s3_endpoint="" \ # S3 API endpoint.

# Alternatively for providing key-value pairs, you can utilize the '--values' option by specifying a file path containing 
# key-value pairs in either JSON or YAML format.
# File content example: {"rclone_config_s3_type":"s3",...}
zenml secret create s3-seldon-secret \
    --values=@path/to/file.json
```

Example of configuring a Seldon Core secret for GCS:

```shell
zenml secret create gs-seldon-secret \
--rclone_config_gs_type="google cloud storage" \ # set to 'google cloud storage' for GCS storage.
--rclone_config_gs_client_secret="" \  # OAuth client secret. 
--rclone_config_gs_token="" \ # OAuth Access Token as a JSON blob.
--rclone_config_gs_project_number="" \ # project number.
--rclone_config_gs_service_account_credentials="" \ #service account credentials JSON blob.
--rclone_config_gs_anonymous=False \ # Access public buckets and objects without credentials. 
# Set to True if you just want to download files and don't configure credentials.
--rclone_config_gs_auth_url="" \ # auth server URL.

# Alternatively for providing key-value pairs, you can utilize the '--values' option by specifying a file path containing 
# key-value pairs in either JSON or YAML format.
# File content example: {"rclone_config_gs_type":"google cloud storage",...}
zenml secret create gs-seldon-secret \
    --values=@path/to/file.json
```

Example of configuring a Seldon Core secret for Azure Blob Storage:

```shell
zenml secret create az-seldon-secret \
--rclone_config_az_type="azureblob" \ # set to 'azureblob' for Azure Blob Storage.
--rclone_config_az_account="" \ # storage Account Name. Leave blank to
# use SAS URL or MSI.
--rclone_config_az_key="" \ # storage Account Key. Leave blank to
# use SAS URL or MSI.
--rclone_config_az_sas_url="" \ # SAS URL for container level access
# only. Leave blank if using account/key or MSI.
--rclone_config_az_use_msi="" \ # use a managed service identity to
# authenticate (only works in Azure).
--rclone_config_az_client_id="" \ # client ID of the service principal
# to use for authentication.
--rclone_config_az_client_secret="" \ # client secret of the service
# principal to use for authentication.
--rclone_config_az_tenant="" \ # tenant ID of the service principal
# to use for authentication.

# Alternatively for providing key-value pairs, you can utilize the '--values' option by specifying a file path containing 
# key-value pairs in either JSON or YAML format.
# File content example: {"rclone_config_az_type":"azureblob",...}
zenml secret create az-seldon-secret \
    --values=@path/to/file.json
```

</details>

## How do you use it?

### Requirements

To run pipelines that deploy models to Seldon, you need the following tools installed locally:

* [Docker](https://www.docker.com)
* [K3D](https://k3d.io/v5.2.1/#installation) (can be installed by running `curl -s https://raw.githubusercontent.com/rancher/k3d/main/install.sh | bash`).

### Stack Component Registration

For registering the model deployer, we need the URL of the Istio Ingress Gateway deployed on the Kubernetes cluster. We can get this URL by running the following command (assuming that the service name is `istio-ingressgateway`, deployed in the `istio-system` namespace):

```bash
# For GKE clusters, the host is the GKE cluster IP address.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
# For EKS clusters, the host is the EKS cluster IP hostname.
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
```

Now register the model deployer:

> **Note**: If you chose to configure your own custom credentials to authenticate to the persistent storage service where models are stored, as covered in the [Advanced: Configuring a Custom Seldon Core Secret](seldon.md#managing-seldon-core-authentication) section, you will need to specify a ZenML secret reference when you configure the Seldon Core model deployer below:
>
> ```shell
> zenml model-deployer register seldon_deployer --flavor=seldon \
>  --kubernetes_context=<KUBERNETES-CONTEXT> \
>  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
>  --base_url=http://$INGRESS_HOST \
>  --secret=<zenml-secret-name> 
> ```

```bash
# Register the Seldon Core Model Deployer
zenml model-deployer register seldon_deployer --flavor=seldon \
  --kubernetes_context=<KUBERNETES-CONTEXT> \
  --kubernetes_namespace=<KUBERNETES-NAMESPACE> \
  --base_url=http://$INGRESS_HOST \
```

We can now use the model deployer in our stack.

```bash
zenml stack update seldon_stack --model-deployer=seldon_deployer
```

See the [seldon\_model\_deployer\_step](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-seldon/#zenml.integrations.seldon.steps.seldon\_deployer.seldon\_model\_deployer\_step) for an example of using the Seldon Core Model Deployer to deploy a model inside a ZenML pipeline step.

### Configuration

Within the `SeldonDeploymentConfig` you can configure:

* `model_name`: the name of the model in the Seldon cluster and in ZenML.
* `replicas`: the number of replicas with which to deploy the model
* `implementation`: the type of Seldon inference server to use for the model. The implementation type can be one of the following: `TENSORFLOW_SERVER`, `SKLEARN_SERVER`, `XGBOOST_SERVER`, `custom`.
* `parameters`: an optional list of parameters (`SeldonDeploymentPredictorParameter`) to pass to the deployment predictor in the form of:
  * `name`
  * `type`
  * `value`
* `resources`: the resources to be allocated to the model. This can be configured by passing a `SeldonResourceRequirements` object with the `requests` and `limits` properties. The values for these properties can be a dictionary with the `cpu` and `memory` keys. The values for these keys can be a string with the amount of CPU and memory to be allocated to the model.
* `serviceAccount` The name of the Service Account applied to the deployment.

For more information and a full list of configurable attributes of the Seldon Core Model Deployer, check out the [SDK Docs](https://sdkdocs.zenml.io/latest/integration\_code\_docs/integrations-seldon/#zenml.integrations.seldon.model\_deployers) .

### Custom Code Deployment

ZenML enables you to deploy your pre- and post-processing code into the deployment environment together with the model by defining a custom predict function that will be wrapped in a Docker container and executed on the model deployment server, e.g.:

```python
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
        model: The model to use for prediction.
        request: The prediction response of the model is an array-like format.
    Returns:
        The prediction in an array-like format.
    """
    inputs = []
    for instance in request:
        input = np.array(instance)
        if not isinstance(input, np.ndarray):
            raise Exception("The request must be a NumPy array")
        processed_input = pre_process(input)
        prediction = model.predict(processed_input)
        postprocessed_prediction = post_process(prediction)
        inputs.append(postprocessed_prediction)
    return inputs


def pre_process(input: np.ndarray) -> np.ndarray:
    """Pre process the data to be used for prediction."""
    input = input / 255.0
    return input[None, :, :]


def post_process(prediction: np.ndarray) -> str:
    """Pre process the data"""
    classes = [str(i) for i in range(10)]
    prediction = tf.nn.softmax(prediction, axis=-1)
    maxindex = np.argmax(prediction.numpy())
    return classes[maxindex]
```

{% hint style="info" %}
The custom predict function should get the model and the input data as arguments and return the model predictions. ZenML will automatically take care of loading the model into memory and starting the `seldon-core-microservice` that will be responsible for serving the model and running the predict function.
{% endhint %}

After defining your custom predict function in code, you can use the `seldon_custom_model_deployer_step` to automatically build your function into a Docker image and deploy it as a model server by setting the `predict_function` argument to the path of your `custom_predict` function:

```python
from zenml.integrations.seldon.steps import seldon_custom_model_deployer_step
from zenml.integrations.seldon.services import SeldonDeploymentConfig
from zenml import pipeline

@pipeline
def seldon_deployment_pipeline():
    model = ...
    seldon_custom_model_deployer_step(
        model=model,
        predict_function="<PATH.TO.custom_predict>",  # TODO: path to custom code
        service_config=SeldonDeploymentConfig(
            model_name="<MODEL_NAME>",  # TODO: name of the deployed model
            replicas=1,
            implementation="custom",
            resources=SeldonResourceRequirements(
                limits={"cpu": "200m", "memory": "250Mi"}
            ),
            serviceAccountName="kubernetes-service-account",
        ),
    )
```

#### Advanced Custom Code Deployment with Seldon Core Integration

{% hint style="warning" %}
Before creating your custom model class, you should take a look at the [custom Python model](https://docs.seldon.io/projects/seldon-core/en/latest/python/python\_wrapping\_docker.html) section of the Seldon Core documentation.
{% endhint %}

The built-in Seldon Core custom deployment step is a good starting point for deploying your custom models. However, if you want to deploy more than the trained model, you can create your own custom class and a custom step to achieve this.

See the [ZenML custom Seldon model class](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-seldon/#zenml.integrations.seldon.custom_deployer.zenml_custom_model.ZenMLCustomModel) as a reference.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
