---
description: Storing artifacts using GCP Cloud Storage.
---

# Google Cloud Storage (GCS)

The GCS Artifact Store is an [Artifact Store](./) flavor provided with the GCP ZenML integration that uses [the Google Cloud Storage managed object storage service](https://cloud.google.com/storage/docs/introduction) to store ZenML artifacts in a GCP Cloud Storage bucket.

### When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](local.md) is usually sufficient if you just want to evaluate ZenML or get started quickly without incurring the trouble and the cost of employing cloud storage services in your stack. However, the local Artifact Store becomes insufficient or unsuitable if you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a Kubeflow or Kubernetes Orchestrator running in a public cloud).
* if you outgrow what your local machine can offer in terms of storage space and need to use some form of private or public storage service that is shared with others
* if you are running pipelines at scale and need an Artifact Store that can handle the demands of production-grade MLOps

In all these cases, you need an Artifact Store that is backed by a form of public cloud or self-hosted shared object storage service.

You should use the GCS Artifact Store when you decide to keep your ZenML artifacts in a shared object storage and if you have access to the Google Cloud Storage managed service. You should consider one of the other [Artifact Store flavors](./#artifact-store-flavors) if you don't have access to the GCP Cloud Storage service.

### How do you deploy it?

{% hint style="info" %}
Would you like to skip ahead and deploy a full ZenML cloud stack already, including a GCS Artifact Store? Check out the[in-browser stack deployment wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack), the [stack registration wizard](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/register-a-cloud-stack), or [the ZenML GCP Terraform module](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/deploy-a-cloud-stack-with-terraform) for a shortcut on how to deploy & register this stack component.
{% endhint %}

The GCS Artifact Store flavor is provided by the GCP ZenML integration, you need to install it on your local machine to be able to register a GCS Artifact Store and add it to your stack:

```shell
zenml integration install gcp -y
```

The only configuration parameter mandatory for registering a GCS Artifact Store is the root path URI, which needs to point to a GCS bucket and take the form `gs://bucket-name`. Please read [the Google Cloud Storage documentation](https://cloud.google.com/storage/docs/creating-buckets) on how to configure a GCS bucket.

With the URI to your GCS bucket known, registering a GCS Artifact Store can be done as follows:

```shell
# Register the GCS artifact store
zenml artifact-store register gs_store -f gcp --path=gs://bucket-name

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a gs_store ... --set
```

Depending on your use case, however, you may also need to provide additional configuration parameters pertaining to [authentication](gcp.md#authentication-methods) to match your deployment scenario.

#### Authentication Methods

Integrating and using a GCS Artifact Store in your pipelines is not possible without employing some form of authentication. If you're looking for a quick way to get started locally, you can use the _Implicit Authentication_ method. However, the recommended way to authenticate to the GCP cloud platform is through [a GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector). This is particularly useful if you are configuring ZenML stacks that combine the GCS Artifact Store with other remote stack components also running in GCP.

{% tabs %}
{% tab title="Implicit Authentication" %}
This method uses the implicit GCP authentication available _in the environment where the ZenML code is running_. On your local machine, this is the quickest way to configure a GCS Artifact Store. You don't need to supply credentials explicitly when you register the GCS Artifact Store, as it leverages the local credentials and configuration that the Google Cloud CLI stores on your local machine. However, you will need to install and set up the Google Cloud CLI on your machine as a prerequisite, as covered in [the Google Cloud documentation](https://cloud.google.com/sdk/docs/install-sdk) , before you register the GCS Artifact Store.

{% hint style="warning" %}
Certain dashboard functionality, such as visualizing or deleting artifacts, is not available when using an implicitly authenticated artifact store together with a deployed ZenML server because the ZenML server will not have permission to access the filesystem.

The implicit authentication method also needs to be coordinated with other stack components that are highly dependent on the Artifact Store and need to interact with it directly to the function. If these components are not running on your machine, they do not have access to the local Google Cloud CLI configuration and will encounter authentication failures while trying to access the GCS Artifact Store:

* [Orchestrators](https://docs.zenml.io/stacks/orchestrators/) need to access the Artifact Store to manage pipeline artifacts
* [Step Operators](https://docs.zenml.io/stacks/step-operators/) need to access the Artifact Store to manage step-level artifacts
* [Model Deployers](https://docs.zenml.io/stacks/model-deployers/) need to access the Artifact Store to load served models

To enable these use cases, it is recommended to use [a GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) to link your GCS Artifact Store to the remote GCS bucket.
{% endhint %}
{% endtab %}

{% tab title="GCP Service Connector (recommended)" %}
To set up the GCS Artifact Store to authenticate to GCP and access a GCS bucket, it is recommended to leverage the many features provided by [the GCP Service Connector](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector) such as auto-configuration, best security practices regarding long-lived credentials and reusing the same credentials across multiple stack components.

If you don't already have a GCP Service Connector configured in your ZenML deployment, you can register one using the interactive CLI command. You have the option to configure a GCP Service Connector that can be used to access more than one GCS bucket or even more than one type of GCP resource:

```sh
zenml service-connector register --type gcp -i
```

A non-interactive CLI example that leverages [the Google Cloud CLI configuration](https://cloud.google.com/sdk/docs/install-sdk) on your local machine to auto-configure a GCP Service Connector targeting a single GCS bucket is:

```sh
zenml service-connector register <CONNECTOR_NAME> --type gcp --resource-type gcs-bucket --resource-name <GCS_BUCKET_NAME> --auto-configure
```

{% code title="Example Command Output" %}
```
$ zenml service-connector register gcs-zenml-bucket-sl --type gcp --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl --auto-configure
⠸ Registering service connector 'gcs-zenml-bucket-sl'...
Successfully registered service connector `gcs-zenml-bucket-sl` with access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠───────────────┼──────────────────────┨
┃ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

> **Note**: Please remember to grant the entity associated with your GCP credentials permissions to read and write to your GCS bucket as well as to list accessible GCS buckets. For a full list of permissions required to use a GCP Service Connector to access one or more GCS buckets, please refer to the [GCP Service Connector GCS bucket resource type documentation](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector#gcs-bucket) or read the documentation available in the interactive CLI commands and dashboard. The GCP Service Connector supports [many different authentication methods](https://docs.zenml.io/how-to/infrastructure-deployment/auth-management/gcp-service-connector#authentication-methods) with different levels of security and convenience. You should pick the one that best fits your use case.

If you already have one or more GCP Service Connectors configured in your ZenML deployment, you can check which of them can be used to access the GCS bucket you want to use for your GCS Artifact Store by running e.g.:

```sh
zenml service-connector list-resources --resource-type gcs-bucket
```

{% code title="Example Command Output" %}
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼─────────────────────────────────────────────────┨
┃ 7f0c69ba-9424-40ae-8ea6-04f35c2eba9d │ gcp-user-account    │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl                            ┃
┃                                      │                     │                │               │ gs://zenml-core.appspot.com                     ┃
┃                                      │                     │                │               │ gs://zenml-core_cloudbuild                      ┃
┃                                      │                     │                │               │ gs://zenml-datasets                             ┃
┃                                      │                     │                │               │ gs://zenml-internal-artifact-store              ┃
┃                                      │                     │                │               │ gs://zenml-kubeflow-artifact-store              ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼─────────────────────────────────────────────────┨
┃ 2a0bec1b-9787-4bd7-8d4a-9a47b6f61643 │ gcs-zenml-bucket-sl │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

After having set up or decided on a GCP Service Connector to use to connect to the target GCS bucket, you can register the GCS Artifact Store as follows:

```sh
# Register the GCS artifact-store and reference the target GCS bucket
zenml artifact-store register <GCS_STORE_NAME> -f gcp \
    --path='gs://your-bucket'

# Connect the GCS artifact-store to the target bucket via a GCP Service Connector
zenml artifact-store connect <GCS_STORE_NAME> -i
```

A non-interactive version that connects the GCS Artifact Store to a target GCP Service Connector:

```sh
zenml artifact-store connect <GCS_STORE_NAME> --connector <CONNECTOR_ID>
```

{% code title="Example Command Output" %}
```
$ zenml artifact-store connect gcs-zenml-bucket-sl --connector gcs-zenml-bucket-sl
Successfully connected artifact store `gcs-zenml-bucket-sl` to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME      │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼─────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ 2a0bec1b-9787-4bd7-8d4a-9a47b6f61643 │ gcs-zenml-bucket-sl │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

As a final step, you can use the GCS Artifact Store in a ZenML Stack:

```sh
# Register and set a stack with the new artifact store
zenml stack register <STACK_NAME> -a <GCS_STORE_NAME> ... --set
```
{% endtab %}

{% tab title="GCP Credentials" %}
When you register the GCS Artifact Store, you can [generate a GCP Service Account Key](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa), store it in a [ZenML Secret](https://docs.zenml.io/getting-started/deploying-zenml/secret-management) and then reference it in the Artifact Store configuration.

This method has some advantages over the implicit authentication method:

* you don't need to install and configure the GCP CLI on your host
* you don't need to care about enabling your other stack components (orchestrators, step operators and model deployers) to have access to the artifact store through GCP Service Accounts and Workload Identity
* you can combine the GCS artifact store with other stack components that are not running in GCP

For this method, you need to [create a user-managed GCP service account](https://cloud.google.com/iam/docs/service-accounts-create), grant it privileges to read and write to your GCS bucket (i.e. use the `Storage Object Admin` role) and then [create a service account key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

With the service account key downloaded to a local file, you can register a ZenML secret and reference it in the GCS Artifact Store configuration as follows:

```shell
# Store the GCP credentials in a ZenML
zenml secret create gcp_secret \
    --token=@path/to/service_account_key.json

# Register the GCS artifact store and reference the ZenML secret
zenml artifact-store register gcs_store -f gcp \
    --path='gs://your-bucket' \
    --authentication_secret=gcp_secret

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a gs_store ... --set

```
{% endtab %}
{% endtabs %}

For more, up-to-date information on the GCS Artifact Store implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/integration_code_docs/integrations-gcp.html#zenml.integrations.gcp) .

### How do you use it?

Aside from the fact that the artifacts are stored in GCP Cloud Storage, using the GCS Artifact Store is no different from [using any other flavor of Artifact Store](./#how-to-use-it).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
