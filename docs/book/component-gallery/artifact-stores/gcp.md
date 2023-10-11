---
description: How to store artifacts using GCP Cloud Storage
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


The GCS Artifact Store is an [Artifact Store](./artifact-stores.md) flavor 
provided with the GCP ZenML integration that uses 
[the Google Cloud Storage managed object storage service](https://cloud.google.com/storage/docs/introduction)
to store ZenML artifacts in a GCP Cloud Storage bucket.

## When would you want to use it?

Running ZenML pipelines with [the local Artifact Store](./local.md) is usually
sufficient if you just want to evaluate ZenML or get started quickly without
incurring the trouble and the cost of employing cloud storage services in your
stack. However, the local Artifact Store becomes insufficient or unsuitable if
you have more elaborate needs for your project:

* if you want to share your pipeline run results with other team members or
stakeholders inside or outside your organization
* if you have other components in your stack that are running remotely (e.g. a
Kubeflow or Kubernetes Orchestrator running in public cloud).
* if you outgrow what your local machine can offer in terms of storage space and
need to use some form of private or public storage service that is shared with
others
* if you are running pipelines at scale and need an Artifact Store that can
handle the demands of production grade MLOps

In all these cases, you need an Artifact Store that is backed by a form of
public cloud or self-hosted shared object storage service.

You should use the GCS Artifact Store when you decide to keep your ZenML
artifacts in a shared object storage and if you have access to the Google Cloud
Storage managed service.
You should consider one of the other [Artifact Store flavors](./artifact-stores.md#artifact-store-flavors)
if you don't have access to the GCP Cloud Storage service.

## How do you deploy it?

The GCS Artifact Store flavor is provided by the GCP ZenML integration, you need
to install it on your local machine to be able to register a GCS Artifact Store
and add it to your stack:

```shell
zenml integration install gcp -y
```

The only configuration parameter mandatory for registering a GCS Artifact Store
is the root path URI, which needs to point to a GCS bucket and takes the form
`gs://bucket-name`. Please read [the Google Cloud Storage documentation](https://cloud.google.com/storage/docs/creating-buckets)
on how to configure a GCS bucket.

With the URI to your GCS bucket known, registering an GCS Artifact Store can be
done as follows:

```shell
# Register the GCS artifact store
zenml artifact-store register gs_store -f gcp --path=gs://bucket-name

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a gs_store ... --set
```

Depending on your use-case, however, you may also need to provide additional
configuration parameters pertaining to [authentication](#authentication-methods)
to match your deployment scenario.

### Authentication Methods

Integrating and using a GCS Artifact Store in your pipelines is not
possible without employing some form of authentication. ZenML currently provides
two options for managing GCS authentication: one for which you don't need to
manage credentials explicitly, the other one that requires you to generate
a GCP Service Account key and store it in a
[ZenML Secret](../../advanced-guide/practical/secrets-management.md). Each
method has advantages and disadvantages, and you should choose the one that
best suits your use-case. If you're looking for a quick way to get started
locally, we recommend using the *Implicit Authentication* method. However, if
you would like to experiment with ZenML stacks that combine the GCS Artifact
Store with other remote stack components, we recommend using the
*GCP Credentials* method, especially if you don't have a lot of experience with
GCP Service Accounts and configuring Workload Identity for GKE.

{% tabs %}
{% tab title="Implicit Authentication" %}

This method uses the implicit GCP authentication available _in the environment
where the ZenML code is running_. On your local machine, this is the quickest
way to configure a GCS Artifact Store. You don't need to supply credentials
explicitly when you register the GCS Artifact Store, as it leverages the local
credentials and configuration that the Google Cloud CLI stores on your local
machine. However, you will need to install and set up the Google Cloud CLI on
your machine as a prerequisite, as covered in [the Google Cloud documentation](https://cloud.google.com/sdk/docs/install-sdk), before you register the GCS Artifact Store.

{% hint style="warning" %}
The implicit authentication method needs to be coordinated with other stack
components that are highly dependent on the Artifact Store and need to interact
with it directly to function. If these components are not running on your
machine, they do not have access to the local Google Cloud CLI configuration and
will encounter authentication failures while trying to access the GCS Artifact
Store:

* [Orchestrators](../orchestrators/orchestrators.md) need to access the 
Artifact Store to manage pipeline artifacts
* [Step Operators](../step-operators/step-operators.md) need to access the 
Artifact Store to manage step level artifacts
* [Model Deployers](../model-deployers/model-deployers.md) need to access the 
Artifact Store to load served models

These remote stack components can still use the implicit authentication method:
if they are also running within Google Kubernetes Engine, ZenML will try to load
credentials from the Google compute metadata service. In order to take advantage
of this feature, you must have configured a [Service Account](https://cloud.google.com/kubernetes-engine/docs/tutorials/authenticating-to-cloud-platform)
with the proper permissions or enabled [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
when you launched your GKE cluster. These mechanisms allow Google workloads like
GKE pods to access other Google services without requiring explicit credentials.

If you have remote stack components that are not running in GKE, or if
you are unsure how to configure them to use Service Accounts or Workload
Identity, you should use one of the other authentication methods.
{% endhint %}

{% endtab %}

{% tab title="GCP Credentials" %}

When you register the GCS Artifact Store, you can
[generate a GCP Service Account Key](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa),
store it in a [ZenML Secret](../../advanced-guide/practical/secrets-management.md)
and then reference it in the Artifact Store configuration.

This method has some advantages over the implicit authentication method:

* you don't need to install and configure the GCP CLI on your host
* you don't need to care about enabling your other stack components
(orchestrators, step operators and model deployers) to have access to the
artifact store through GCP Service Accounts and Workload Identity
* you can combine the GCS artifact store with other stack components that are
not running in GCP

For this method, you need to [create a user-managed GCP service account](https://cloud.google.com/iam/docs/service-accounts-create), grant it privileges to read and write to your GCS
bucket (i.e. use the `Storage Object Admin` role) and then
[create a service account key](https://cloud.google.com/iam/docs/keys-create-delete#creating).

With the service account key downloaded to a local file, you can register a ZenML
secret and reference it in the GCS Artifact Store configuration as follows:

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

For more, up-to-date information on the GCS Artifact Store implementation and its
configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/integration_code_docs/integrations-gcp/#zenml.integrations.gcp.artifact_stores.gcp_artifact_store).

## How do you use it?

Aside from the fact that the artifacts are stored in GCP Cloud Storage,
using the GCS Artifact Store is no different from [using any other flavor of Artifact Store](./artifact-stores.md#how-to-use-it).
