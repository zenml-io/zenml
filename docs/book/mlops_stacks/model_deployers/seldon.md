---
description: Deploy Machine Learning model to Kubernetes with Seldon Core
---

The Seldon Core Model Deployer is one of the available flavors of the [Model Deployer](./overview.md) 
stack component. Provided with the MLFLow integration it can be used to deploy
and manage models on a inference server running on top of a Kubernetes cluster.

## How do you deploy it?

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
You can use one of the supported [remote storage flavors](../artifact_stores/overview.md) to store your models as part of your stack

Since the Seldon Model Deployer is interacting with the Seldon Core model server deployed on 
a Kubernetes cluster, you need to provide a set of configuration parameters. These parameters are:

* kubernetes_context: the Kubernetes context to use to contact the remote Seldon Core installation. If not specified, the current configuration is used. Depending on where the Seldon model deployer is being used
* kubernetes_namespace: the Kubernetes namespace where the Seldon Core deployment servers 
are provisioned and managed by ZenML. If not specified, the namespace set in the current configuration is used.
* base_url: the base URL of the Kubernetes ingress used to expose the Seldon Core deployment servers.
* secret: the name of a ZenML secret containing the credentials used by Seldon Core storage initializers to authenticate to the Artifact Store

We can then register the model deployer and use it in our active stack:

```bash
zenml model-deployer register seldon_deployer --flavor=seldon \
  --kubernetes_context=zenml-eks \
  --kubernetes_namespace=zenml-workloads \
  --base_url=http://$INGRESS_HOST \
  --secret=s3-store-credentials

# Now we can use the model deployer in our stack
zenml stack update seldon_stack --model-deployer=seldon_deployer
```

#### Managing Seldon Core Credentials

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
[Secrets Manager](../secrets_managers/overview.md).

The following is an example of registering an S3 secret with the Seldon Core model deployer:

```shell
$ zenml secret register -s seldon_s3 s3-store \
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

$ zenml secret get s3-store
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

A concrete example of using the Seldon Core Model Deployer can be found
[here](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration).

For more information and a full list of configurable attributes of the Seldon Core Model Deployer, check out the 
[API Docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.seldon.model_deployers).