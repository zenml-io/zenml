---
description: Store artifacts in an AWS S3 or compatible bucket
---

The S3 Artifact Store is an [Artifact Store](./overview.md) flavor provided with
the S3 ZenML integration that uses [the AWS S3 managed object storage service](https://aws.amazon.com/s3/)
or one of the self-hosted S3 alternatives, such as [MinIO](https://min.io/) or
[Ceph RGW](https://ceph.io/en/discover/technology/#object).
to store artifacts in an S3 compatible object storage backend.

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

You should use the S3 Artifact Store when you decide to keep your ZenML
artifacts in a shared object storage and if you have access to the AWS S3
managed service or one of the S3 compatible alternatives (e.g. Minio, Ceph RGW).
You should consider one of the other [Artifact Store flavors](./overview.md#artifact-store-flavors)
if you don't have access to an S3 compatible service.

## How do you deploy it?

The S3 Artifact Store flavor is provided by the S3 ZenML integration, you need
to install it on your local machine to be able to register an S3 Artifact Store
and add it to your stack:

```shell
zenml integration install s3 -y
```

The only configuration parameter mandatory for registering an S3 Artifact Store
is the root path URI, which needs to point to an S3 bucket and takes the form
`s3://bucket-name`. Please read the documentation relevant to the S3 service
that you are using on how to create an S3 bucket. For example, the AWS S3
documentation is available [here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html).

With the URI to your S3 bucket known, registering an S3 Artifact Store and using
it in a stack can be done as follows:

```shell
# Register the S3 artifact-store
zenml artifact-store register s3_store -f s3 --path=s3://bucket-name

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a s3_store ... --set
```

Depending on your use-case, however, you may also need to provide additional
configuration parameters pertaining to [authentication](#authentication-methods)
or [pass advanced configuration parameters](#advanced-configuration) to match
your S3 compatible service or deployment scenario.

{% hint style="info" %}
Configuring an S3 Artifact Store in can be a complex and error prone process,
especially if you plan on using it alongside other stack components running in
the AWS cloud. You might consider referring to the [ZenML Cloud Guide](../../cloud-guide/overview.md)
for a more holistic approach to configuring full AWS-based stacks for ZenML.
{% endhint %}

### Authentication Methods

Integrating and using an S3 compatible Artifact Store in your pipelines is not
possible without employing some form of authentication. ZenML currently provides
three options for configuring S3 credentials, the recommended one being to
use a [Secrets Manager](../secrets_managers/overview.md) in your stack to store
the sensitive information in a secure location.

{% tabs %}
{% tab title="Implicit Authentication" %}

This method uses the implicit AWS authentication available _in the environment
where the ZenML code is running_. On your local machine, this is the quickest
way to configure an S3 Artifact Store. You don't need to supply credentials
explicitly when you register the S3 Artifact Store, as it leverages the local
credentials and configuration that the AWS CLI stores on your local
machine. However, you will need to install and set up the AWS CLI on your
machine as a prerequisite, as covered in [the AWS CLI documentation](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), before you register the S3 Artifact Store.

{% hint style="warning" %}
The implicit authentication method needs to be coordinated with other stack
components that are highly dependent on the Artifact Store and need to interact
with it directly to function. If these components are not running on your
machine, they do not have access to the local AWS CLI configuration and will
encounter authentication failures while trying to access the S3 Artifact Store:

* [Orchestrators](../orchestrators/overview.md) need to access the Artifact
Store to manage pipeline artifacts
* [Step Operators](../step_operators/overview.md) need to access the Artifact
Store to manage step level artifacts
* [Model Deployers](../model_deployers/overview.md) need to access the Artifact
Store to load served models

These remote stack components can still use the implicit authentication method:
if they are also running on Amazon EC2 or EKS nodes, ZenML will try to load
credentials from the instance metadata service. In order to take advantage of
this feature, you must have specified an IAM role to use when you launched your
EC2 instance or EKS cluster. This mechanism allows AWS workloads like EC2
instances and EKS pods to access other AWS services without requiring explicit
credentials. For more information on how to configure IAM roles:

* on EC2 instances, see the [IAM Roles for Amazon EC2 guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
* on EKS clusters, see the [Amazon EKS cluster IAM role guide](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html)

If you have remote stack components that are not running in AWS Cloud, or if you
are unsure how to configure them to use IAM roles, you should use one of the
other authentication methods.
{% endhint %}

{% endtab %}

{% tab title="Explicit Credentials" %}

Use this method to store the S3 credentials in the Artifact Store configuration.
When you register the S3 Artifact Store, you may include the credentials
directly in the Artifact Store configuration. This has the advantage that you
don't need to install and configure the AWS CLI or set up a Secrets Manager in
your stack, but the credentials won't be stored securely and will be visible in
the stack configuration:

```shell
# Register the S3 artifact-store
zenml artifact-store register s3_store -f s3 \
    --path='s3://your-bucket' \
    --key='your-S3-access-key-ID' \
    --secret='your-S3-secret-key' \
    --token='your-S3-token'

# Register and set a stack with the new artifact store
zenml stack register custom_stack -a s3_store ... --set
```

{% endtab %}

{% tab title="Secrets Manager (Recommended)" %}

This method requires using a [Secrets Manager](../secrets_managers/overview.md)
in your stack to store the sensitive S3 authentication information in a secure
location.

The S3 credentials are configured as a ZenML secret that is referenced in the
Artifact Store configuration, e.g.:

```shell
# Register the S3 artifact store
zenml artifact-store register s3_store -f s3 \
    --path='s3://your-bucket' \
    --authentication_secret=s3_secret

# Register a secrets manager
zenml secrets-manager register secrets_manager \
    --flavor=<FLAVOR_OF_YOUR_CHOICE> ...

# Register and set a stack with the new artifact store and secrets manager
zenml stack register custom_stack -a s3_store -x secrets_manager ... --set

# Create the secret referenced in the artifact store
zenml secret register s3_secret -s aws \
    --aws_access_key_id='your-S3-access-key-ID' \
    --aws_secret_access_key='your-S3-secret-key' \
    --aws_session_token='your-S3-token'
```

{% endtab %}
{% endtabs %}

### Advanced Configuration

The S3 Artifact Store accepts a range of advanced configuration options that can
be used to further customize how ZenML connects to the S3 storage service that
you are using. These are accessible via the `client_kwargs`, `config_kwargs` and
`s3_additional_kwargs` configuration attributes and are passed transparently to
[the underlying S3Fs library](https://s3fs.readthedocs.io/en/latest/#s3-compatible-storage):

* `client_kwargs`: arguments that will be transparently passed to
[the botocore client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html#boto3.session.Session.client).
You can use it to configure parameters like `endpoint_url` and `region_name`
when connecting to an S3 compatible endpoint (e.g. Minio).
* `config_kwargs`: advanced parameters passed to [botocore.client.Config](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/config.html).
* `s3_additional_kwargs`: advanced parameters that are used when calling S3 API,
typically used for things like `ServerSideEncryption` and `ACL`.

To include these advanced parameters in your Artifact Store configuration, pass
them using JSON format during registration, e.g.:

```shell
zenml artifact-store register minio_store -f s3 \
    --path='s3://minio_bucket' \
    --authentication_secret=s3_secret
    --client_kwargs='{"endpoint_url:"http://minio.cluster.local:9000", "region_name":"us-east-1"}'
```

For more, up-to-date information on the S3 Artifact Store implementation and its
configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.s3.artifact_stores.s3_artifact_store).

## How do you use it?

Aside from the fact that the artifacts are stored in an S3 compatible backend,
using the S3 Artifact Store is no different than [using any other flavor of Artifact Store](./overview.md#how-to-use-it).
