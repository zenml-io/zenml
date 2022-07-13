---
description: Store artifacts using GCP Cloud Storage
---

The GCS Artifact Store is an [Artifact Store](./overview.md) flavor provided with
the GCP ZenML integration that uses [the Google Cloud Storage managed object storage service](https://cloud.google.com/storage/docs/introduction)
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
You should consider one of the other [Artifact Store flavors](./overview.md#artifact-store-flavors)
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

{% hint style="info" %}
Configuring a GCS Artifact Store in can be a complex and error prone process,
especially if you plan on using it alongside other stack components running in
the Google cloud. You might consider referring to the [ZenML Cloud Guide](../../cloud-guide/overview.md)
for a more holistic approach to configuring full GCP-based stacks for ZenML.
{% endhint %}

### Authentication Methods

Integrating and using a GCS Artifact Store in your pipelines is not
possible without employing some form of authentication. ZenML currently provides
two options for configuring GCP credentials, the recommended one being to use
a [Secrets Manager](../secrets_managers/overview.md) in your stack to store the
sensitive information in a secure location.

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

* [Orchestrators](../orchestrators/overview.md) need to access the Artifact
Store to manage pipeline artifacts
* [Step Operators](../step_operators/overview.md) need to access the Artifact
Store to manage step level artifacts
* [Model Deployers](../model_deployers/overview.md) need to access the Artifact
Store to load served models

These remote stack components can still use the implicit authentication method:
if they are also running within Google Kubernetes Engine, ZenML will try to load
credentials from the Google compute metadata service. In order to take advantage
of this feature, you must have configured a [Service Account](https://cloud.google.com/kubernetes-engine/docs/tutorials/authenticating-to-cloud-platform)
with the proper permissions or enabled [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
when you launched your GKE cluster. These mechanisms allows Google workloads like
GKE pods to access other Google services without requiring explicit credentials.

If you have remote stack components that are not running in GKE, or if
you are unsure how to configure them to use Service Accounts or Workload
Identity, you should use one of the other authentication methods.
{% endhint %}

{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires using a [Secrets Manager](../secrets_managers/overview.md)
in your stack to store the sensitive GCP authentication information in a secure
location.

A Google access key needs to be generated using the [gcloud](https://cloud.google.com/sdk/docs/)
utility or Google Cloud console, as covered [here](https://cloud.google.com/docs/authentication/getting-started#creating_a_service_account). This comes in the form of a file
containing JSON credentials.

The GCP credentials are configured as a ZenML secret that is referenced in the
Artifact Store configuration, e.g.:

```shell
# Register the GCS artifact store
zenml artifact-store register gcs_store -f gcp \
    --path='gs://your-bucket' \
    --authentication_secret=gcp_secret

# Register a secrets manager
zenml secrets-manager register secrets_manager \
    --flavor=<FLAVOR_OF_YOUR_CHOICE> ...

# Register and set a stack with the new artifact store and secrets manager
zenml stack register custom_stack -a gs_store -x secrets_manager ... --set

# Create the secret referenced in the artifact store
zenml secret register gcp_secret -s gcp \
    --token=@path/to/token/file.json
```

{% endtab %}
{% endtabs %}

For more, up-to-date information on the GCS Artifact Store implementation and its
configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.gcp.artifact_stores.gcp_artifact_store).

## How do you use it?

Aside from the fact that the artifacts are stored in GCP Cloud Storage,
using the GCS Artifact Store is no different than [using any other flavor of Artifact Store](./overview.md#how-to-use-it).
