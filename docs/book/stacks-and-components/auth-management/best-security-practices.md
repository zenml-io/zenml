---
description: >-
  Best practices concerning the various authentication methods implemented by
  Service Connectors.
---

# Security best practices

Service Connector Types, especially those targeted at cloud providers, offer a plethora of authentication methods matching those supported by remote cloud platforms. While there is no single authentication standard that unifies this process, there are some patterns that are easily identifiable and can be used as guidelines when deciding which authentication method to use to configure a Service Connector.

This section explores some of those patterns and gives some advice regarding which authentication methods are best suited for your needs.

{% hint style="info" %}
This section may require some general knowledge about authentication and authorization to be properly understood. We tried to keep it simple and limit ourselves to talking about high-level concepts, but some areas may get a bit too technical.
{% endhint %}

## Username and password

{% hint style="danger" %}
The key takeaway is this: you should avoid using your primary account password as authentication credentials as much as possible. If there are alternative authentication methods that you can use or other types of credentials (e.g. session tokens, API keys, API tokens), you should always try to use those instead.

Ultimately, if you have no choice, be cognizant of the third parties you share your passwords with. If possible, they should never leave the premises of your local host or development environment.
{% endhint %}

This is the typical authentication method that uses a username or account name plus the associated password. While this is the de facto method used to log in with web consoles and local CLIs, this is the least secure of all authentication methods and _never_ something you want to share with other members of your team or organization or use to authenticate automated workloads.

In fact, cloud platforms don't even allow using user account passwords directly as a credential when authenticating to the cloud platform APIs. There is always a process in place that allows exchanging the account/password credential for [another form of long-lived credential](best-security-practices.md#long-lived-credentials-api-keys-account-keys).

Even when passwords are mentioned as credentials, some services (e.g. DockerHub) also allow using an API access key in place of the user account password.

## Implicit authentication

{% hint style="info" %}
The key takeaway here is that implicit authentication gives you immediate access to some cloud resources and requires no configuration, but it may take some extra effort to expand the range of resources that you're initially allowed to access with it. This is not an authentication method you want to use if you're interested in portability and enabling others to reproduce your results.
{% endhint %}

{% hint style="warning" %}
This method may constitute a security risk, because it can give users access to the same cloud resources and services that the ZenML Server itself is configured to access. For this reason, all implicit authentication methods are disabled by default and need to be explicitly enabled by setting the `ZENML_ENABLE_IMPLICIT_AUTH_METHODS` environment variable or the helm chart `enableImplicitAuthMethods` configuration option to `true` in the ZenML deployment.
{% endhint %}

Implicit authentication is just a fancy way of saying that the Service Connector will use locally stored credentials, configuration files, environment variables, and basically any form of authentication available in the environment where it is running, either locally or in the cloud.

Most cloud providers and their associated Service Connector Types include some form of implicit authentication that is able to automatically discover and use the following forms of authentication in the environment where they are running:

* configuration and credentials set up and stored locally through the cloud platform CLI
* configuration and credentials passed as environment variables
* some form of implicit authentication attached to the workload environment itself. This is only available in virtual environments that are already running inside the same cloud where other resources are available for use. This is called differently depending on the cloud provider in question, but they are essentially the same thing:
  * in AWS, if you're running on Amazon EC2, ECS, EKS, Lambda, or some other form of AWS cloud workload, credentials can be loaded directly from _the instance metadata service._ This [uses the IAM role attached to your workload](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) to authenticate to other AWS services without the need to configure explicit credentials.
  * in GCP, a similar _metadata service_ allows accessing other GCP cloud resources via [the service account attached to the GCP workload](https://cloud.google.com/docs/authentication/application-default-credentials#attached-sa) (e.g. GCP VMs or GKE clusters).
  * in Azure, the [Azure Managed Identity](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview) services can be used to gain access to other Azure services without requiring explicit credentials

There are a few caveats that you should be aware of when choosing an implicit authentication method. It may seem like the easiest way out, but it carries with it some implications that may impact portability and usability later down the road:

* when used with a local ZenML deployment, like the default deployment, or [a local ZenML server started with `zenml up`](../../user-guide/production-guide/README.md), the implicit authentication method will use the configuration files and credentials or environment variables set up _on your local machine_. These will not be available to anyone else outside your local environment and will also not be accessible to workloads running in other environments on your local host. This includes for example local K3D Kubernetes clusters and local Docker containers.
* when used with a remote ZenML server, the implicit authentication method only works if your ZenML server is deployed in the same cloud as the one supported by the Service Connector Type that you are using. For instance, if you're using the AWS Service Connector Type, then the ZenML server must also be deployed in AWS (e.g. in an EKS Kubernetes cluster). You may also need to manually adjust the cloud configuration of the remote cloud workload where the ZenML server is running to allow access to resources (e.g. add permissions to the AWS IAM role attached to the EC2 or EKS node, add roles to the GCP service account attached to the GKE cluster nodes).

<details>

<summary>GCP implicit authentication method example</summary>

The following is an example of using the GCP Service Connector's implicit authentication method to gain immediate access to all the GCP resources that the ZenML server also has access to. Note that this is only possible because the ZenML server is also deployed in GCP, in a GKE cluster, and the cluster is attached to a GCP service account with permissions to access the project resources:

```sh
zenml service-connector register gcp-implicit --type gcp --auth-method implicit --project_id=zenml-core
```

{% code title="Example Command Output" %}
```text
Successfully registered service connector `gcp-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                  ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                      ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ gs://annotation-gcp-store                       ┃
┃                       │ gs://zenml-bucket-sl                            ┃
┃                       │ gs://zenml-core.appspot.com                     ┃
┃                       │ gs://zenml-core_cloudbuild                      ┃
┃                       │ gs://zenml-datasets                             ┃
┃                       │ gs://zenml-internal-artifact-store              ┃
┃                       │ gs://zenml-kubeflow-artifact-store              ┃
┃                       │ gs://zenml-project-time-series-bucket           ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenml-test-cluster                              ┃
┠───────────────────────┼─────────────────────────────────────────────────┨
┃  🐳 docker-registry   │ gcr.io/zenml-core                               ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}
</details>

### Long-lived credentials (API keys, account keys)

{% hint style="success" %}
This is the magic formula of authentication methods. When paired with another ability, such as [automatically generating short-lived API tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials), or [impersonating accounts or assuming roles](best-security-practices.md#impersonating-accounts-and-assuming-roles), this is the ideal authentication mechanism to use, particularly when using ZenML in production and when sharing results with other members of your ZenML team.
{% endhint %}

As a general best practice, but implemented particularly well for cloud platforms, account passwords are never directly used as a credential when authenticating to the cloud platform APIs. There is always a process in place that exchanges the account/password credential for another type of long-lived credential:

* AWS uses the [`aws configure` CLI command](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
* GCP offers [the `gcloud auth application-default login` CLI commands](https://cloud.google.com/docs/authentication/provide-credentials-adc#how\_to\_provide\_credentials\_to\_adc)
* Azure provides [the `az login` CLI command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)

None of your original login information is stored on your local machine or used to access workloads. Instead, an API key, account key or some other form of intermediate credential is generated and stored on the local host and used to authenticate to remote cloud service APIs.

{% hint style="info" %}
When using auto-configuration with Service Connector registration, this is usually the type of credentials automatically identified and extracted from your local machine.
{% endhint %}

Different cloud providers use different names for these types of long-lived credentials, but they usually represent the same concept, with minor variations regarding the identity information and level of permissions attached to them:

* AWS has [Account Access Keys](https://docs.aws.amazon.com/powershell/latest/userguide/pstools-appendix-sign-up.html) and [IAM User Access Keys](https://docs.aws.amazon.com/IAM/latest/UserGuide/id\_credentials\_access-keys.html)
* GCP has [User Account Credentials](https://cloud.google.com/docs/authentication#user-accounts) and [Service Account Credentials](https://cloud.google.com/docs/authentication#service-accounts)

Generally speaking, a differentiation is being made between the following two classes of credentials:

* _user credentials_: credentials representing a human user and usually directly tied to a user account identity. These credentials are usually associated with a broad spectrum of permissions and it is therefore not recommended to share them or make them available outside the confines of your local host.
* _service credentials:_ credentials used with automated processes and programmatic access, where humans are not directly involved. These credentials are not directly tied to a user account identity, but some other form of accounting like a service account or an IAM user devised to be used by non-human actors. It is also usually possible to restrict the range of permissions associated with this class of credentials, which makes them better candidates for sharing them with a larger audience.

ZenML cloud provider Service Connectors can use both classes of credentials, but you should aim to use _service credentials_ as often as possible instead of _user credentials_, especially in production environments. Attaching automated workloads like ML pipelines to service accounts instead of user accounts acts as an extra layer of protection for your user identity and facilitates enforcing another security best practice called [_"the least-privilege principle"_](https://en.wikipedia.org/wiki/Principle\_of\_least\_privilege)_:_ granting each actor only the minimum level of permissions required to function correctly.

Using long-lived credentials on their own still isn't ideal, because if leaked, they pose a security risk, even when they have limited permissions attached. The good news is that ZenML Service Connectors include additional mechanisms that, when used in combination with long-lived credentials, make it even safer to share long-lived credentials with other ZenML users and automated workloads:

* automatically [generating temporary credentials](best-security-practices.md#generating-temporary-and-down-scoped-credentials) from long-lived credentials and even downgrading their permission scope to enforce the least-privilege principle
* implementing [authentication schemes that impersonate accounts and assume roles](best-security-practices.md#impersonating-accounts-and-assuming-roles)

### Generating temporary and down-scoped credentials

Most [authentication methods that utilize long-lived credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) also implement additional mechanisms that help reduce the accidental credentials exposure and risk of security incidents even further, making them ideal for production.

_**Issuing temporary credentials**_: this authentication strategy keeps long-lived credentials safely stored on the ZenML server and away from the eyes of actual API clients and people that need to authenticate to the remote resources. Instead, clients are issued API tokens that have a limited lifetime and expire after a given amount of time. The Service Connector is able to generate these API tokens from long-lived credentials on a need-to-have basis. For example, the AWS Service Connector's "Session Token", "Federation Token" and "IAM Role" authentication methods and basically all authentication methods supported by the GCP Service Connector support this feature.

<details>

<summary>AWS temporary credentials example</summary>

The following example shows the difference between the long-lived AWS credentials configured for an AWS Service Connector and kept on the ZenML server and the temporary Kubernetes API token credentials that the client receives and uses to access the resource.

First, showing the long-lived AWS credentials configured for the AWS Service Connector:

```sh
zenml service-connector describe eks-zenhacks-cluster
```

{% code title="Example Command Output" %}
```text
Service connector 'eks-zenhacks-cluster' of type 'aws' with id 'be53166a-b39c-4e39-8e31-84658e50eec4' is owned by user 'default' and is 'private'.
   'eks-zenhacks-cluster' aws Service Connector Details    
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ be53166a-b39c-4e39-8e31-84658e50eec4 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ NAME             │ eks-zenhacks-cluster                 ┃
┠──────────────────┼──────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ AUTH METHOD      │ session-token                        ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ RESOURCE NAME    │ zenhacks-cluster                     ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SECRET ID        │ fa42ab38-3c93-4765-a4c6-9ce0b548a86c ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SESSION DURATION │ 43200s                               ┃
┠──────────────────┼──────────────────────────────────────┨
┃ EXPIRES IN       │ N/A                                  ┃
┠──────────────────┼──────────────────────────────────────┨
┃ OWNER            │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ WORKSPACE        │ default                              ┃
┠──────────────────┼──────────────────────────────────────┨
┃ SHARED           │ ➖                                   ┃
┠──────────────────┼──────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-16 10:15:26.393769           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-16 10:15:26.393772           ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            Configuration            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE     ┃
┠───────────────────────┼───────────┨
┃ region                │ us-east-1 ┃
┠───────────────────────┼───────────┨
┃ aws_access_key_id     │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_secret_access_key │ [HIDDEN]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┛
```
{% endcode %}

Then, showing the temporary credentials that are issued to clients.  Note the expiration time on the Kubernetes API token:

```sh
zenml service-connector describe eks-zenhacks-cluster --client
```

{% code title="Example Command Output" %}
```text
Service connector 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' of type 'kubernetes' with id 'be53166a-b39c-4e39-8e31-84658e50eec4' is owned by user 'default' and is 'private'.
 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' kubernetes Service 
                                    Connector Details                                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ ID               │ be53166a-b39c-4e39-8e31-84658e50eec4                                ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ NAME             │ eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client) ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🌀 kubernetes                                                       ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ token                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🌀 kubernetes-cluster                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster         ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m57s                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-16 10:17:46.931091                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-16 10:17:46.931094                                          ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
                                           Configuration                                            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE                                                                    ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ server                │ https://A5F8F4142FB12DDCDE9F21F6E9B07A18.gr7.us-east-1.eks.amazonaws.com ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ insecure              │ False                                                                    ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ cluster_name          │ arn:aws:eks:us-east-1:715803424590:cluster/zenhacks-cluster              ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ token                 │ [HIDDEN]                                                                 ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────┨
┃ certificate_authority │ [HIDDEN]                                                                 ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

_**Issuing downscoped credentials**_: in addition to the above, some authentication methods also support restricting the generated temporary API tokens to the minimum set of permissions required to access the target resource or set of resources. This is currently available for the AWS Service Connector's "Federation Token" and "IAM Role" authentication methods.

<details>

<summary>AWS down-scoped credentials example</summary>

It's not easy to showcase this without using some ZenML Python Client code, but here is an example that proves that the AWS client token issued to an S3 client can only access the S3 bucket resource it was issued for, even if the originating AWS Service Connector is able to access multiple S3 buckets with the corresponding long-lived credentials:

```sh
zenml service-connector register aws-federation-multi --type aws --auth-method=federation-token --auto-configure 
```

{% code title="Example Command Output" %}
```text
Successfully registered service connector `aws-federation-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://aws-ia-mwaa-715803424590                ┃
┃                       │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┃                       │ s3://zenml-public-datasets                   ┃
┃                       │ s3://zenml-public-swagger-spec               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The next part involves running some ZenML Python code to showcase that the downscoped credentials issued to a client are indeed restricted to the S3 bucket that the client asked to access:

```python
from zenml.client import Client

client = Client()

# Get a Service Connector client for a particular S3 bucket
connector_client = client.get_service_connector_client(
    name_id_or_prefix="aws-federation-multi",
    resource_type="s3-bucket",
    resource_id="s3://zenfiles"
)

# Get the S3 boto3 python client pre-configured and pre-authenticated
# from the Service Connector client
s3_client = connector_client.connect()

# Verify access to the chosen S3 bucket using the temporary token that
# was issued to the client.
s3_client.head_bucket(Bucket="zenfiles")

# Try to access another S3 bucket that the original AWS long-lived credentials can access.
# An error will be thrown indicating that the bucket is not accessible.
s3_client.head_bucket(Bucket="zenml-demos")
```

{% code title="Example Output" %}
```text
>>> from zenml.client import Client
>>> 
>>> client = Client()
Unable to find ZenML repository in your current working directory (/home/stefan/aspyre/src/zenml) or any parent directories. If you want to use an existing repository which is in a different location, set the environment variable 'ZENML_REPOSITORY_PATH'. If you want to create a new repository, run zenml init.
Running without an active repository root.
>>> 
>>> # Get a Service Connector client for a particular S3 bucket
>>> connector_client = client.get_service_connector_client(
...     name_id_or_prefix="aws-federation-multi",
...     resource_type="s3-bucket",
...     resource_id="s3://zenfiles"
... )
>>> 
>>> # Get the S3 boto3 python client pre-configured and pre-authenticated
>>> # from the Service Connector client
>>> s3_client = connector_client.connect()
>>> 
>>> # Verify access to the chosen S3 bucket using the temporary token that
>>> # was issued to the client.
>>> s3_client.head_bucket(Bucket="zenfiles")
{'ResponseMetadata': {'RequestId': '62YRYW5XJ1VYPCJ0', 'HostId': 'YNBXcGUMSOh90AsTgPW6/Ra89mqzfN/arQq/FMcJzYCK98cFx53+9LLfAKzZaLhwaiJTm+s3mnU=', 'HTTPStatusCode': 200, 'HTTPHeaders': {'x-amz-id-2': 'YNBXcGUMSOh90AsTgPW6/Ra89mqzfN/arQq/FMcJzYCK98cFx53+9LLfAKzZaLhwaiJTm+s3mnU=', 'x-amz-request-id': '62YRYW5XJ1VYPCJ0', 'date': 'Fri, 16 Jun 2023 11:04:20 GMT', 'x-amz-bucket-region': 'us-east-1', 'x-amz-access-point-alias': 'false', 'content-type': 'application/xml', 'server': 'AmazonS3'}, 'RetryAttempts': 0}}
>>> 
>>> # Try to access another S3 bucket that the original AWS long-lived credentials can access.
>>> # An error will be thrown indicating that the bucket is not accessible.
>>> s3_client.head_bucket(Bucket="zenml-demos")
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ <stdin>:1 in <module>                                                                            │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:508 in        │
│ _api_call                                                                                        │
│                                                                                                  │
│    505 │   │   │   │   │   f"{py_operation_name}() only accepts keyword arguments."              │
│    506 │   │   │   │   )                                                                         │
│    507 │   │   │   # The "self" in this scope is referring to the BaseClient.                    │
│ ❱  508 │   │   │   return self._make_api_call(operation_name, kwargs)                            │
│    509 │   │                                                                                     │
│    510 │   │   _api_call.__name__ = str(py_operation_name)                                       │
│    511                                                                                           │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:915 in        │
│ _make_api_call                                                                                   │
│                                                                                                  │
│    912 │   │   if http.status_code >= 300:                                                       │
│    913 │   │   │   error_code = parsed_response.get("Error", {}).get("Code")                     │
│    914 │   │   │   error_class = self.exceptions.from_code(error_code)                           │
│ ❱  915 │   │   │   raise error_class(parsed_response, operation_name)                            │
│    916 │   │   else:                                                                             │
│    917 │   │   │   return parsed_response                                                        │
│    918                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
ClientError: An error occurred (403) when calling the HeadBucket operation: Forbidden
```
{% endcode %}

</details>

### Impersonating accounts and assuming roles

{% hint style="success" %}
These types of authentication methods require more work to set up because multiple permission-bearing accounts and roles need to be provisioned in advance depending on the target audience. On the other hand, they also provide the most flexibility and control. Despite their operational cost, if you are a platform engineer and have the infrastructure know-how necessary to understand and set up the authentication resources, this is for you.
{% endhint %}

These authentication methods deliver another way of [configuring long-lived credentials](best-security-practices.md#long-lived-credentials-api-keys-account-keys) in your Service Connectors without exposing them to clients. They are especially useful as an alternative to cloud provider Service Connectors authentication methods that do not support [automatically downscoping the permissions of issued temporary tokens](best-security-practices.md#generating-temporary-and-down-scoped-credentials).

The processes of account impersonation and role assumption are very similar and can be summarized as follows:

* you configure a Service Connector with long-lived credentials associated with a primary user account or primary service account (preferable). As a best practice, it is common to attach a reduced set of permissions or even no permissions to these credentials other than those that allow the account impersonation or role assumption operation. This makes it more difficult to do any damage if the primary credentials are accidentally leaked.
* in addition to the primary account and its long-lived credentials, you also need to provision one or more secondary access entities in the cloud platform bearing the effective permissions that will be needed to access the target resource(s):
  * one or more IAM roles (to be assumed)
  * one or more service accounts (to be impersonated)
* the Service Connector configuration also needs to contain the name of a target IAM role to be assumed or a service account to be impersonated.
* upon request, the Service Connector will exchange the long-lived credentials associated with the primary account for short-lived API tokens that only have the permissions associated with the target IAM role or service account. These temporary credentials are issued to clients and used to access the target resource, while the long-lived credentials are kept safe and never have to leave the ZenML server boundary.

<details>

<summary>GCP account impersonation example</summary>

For this example, we have the following set up in GCP:

* a primary `empty-connectors@zenml-core.iam.gserviceaccount.com` GCP service account with no permissions whatsoever aside from the "Service Account Token Creator" role that allows it to impersonate the secondary service account below. We also generate a service account key for this account.
* a secondary `zenml-bucket-sl@zenml-core.iam.gserviceaccount.com` GCP service account that only has permissions to access the `zenml-bucket-sl` GCS bucket

First, let's show that the `empty-connectors` service account has no permissions to access any GCS buckets or any other resources for that matter. We'll register a regular GCP Service Connector that uses the service account key (long-lived credentials) directly:

```sh
zenml service-connector register gcp-empty-sa --type gcp --auth-method service-account --service_account_json=@empty-connectors@zenml-core.json --project_id=zenml-core
```

{% code title="Example Command Output" %}
```text
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-empty-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                                                                               ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┨
┃    🔵 gcp-generic     │ zenml-core                                                                                   ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┨
┃     📦 gcs-bucket     │ 💥 error: connector authorization failure: failed to list GCS buckets: 403 GET               ┃
┃                       │ https://storage.googleapis.com/storage/v1/b?project=zenml-core&projection=noAcl&prettyPrint= ┃
┃                       │ false: empty-connectors@zenml-core.iam.gserviceaccount.com does not have                     ┃
┃                       │ storage.buckets.list access to the Google Cloud project. Permission 'storage.buckets.list'   ┃
┃                       │ denied on resource (or it may not exist).                                                    ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ 💥 error: connector authorization failure: Failed to list GKE clusters: 403 Required         ┃
┃                       │ "container.clusters.list" permission(s) for "projects/20219041791". [request_id:             ┃
┃                       │ "0xcb7086235111968a"                                                                         ┃
┃                       │ ]                                                                                            ┃
┠───────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────┨
┃  🐳 docker-registry   │ gcr.io/zenml-core                                                                            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

Next, we'll register a GCP Service Connector that actually uses account impersonation to access the `zenml-bucket-sl` GCS bucket and verify that it can actually access the bucket:

```sh
zenml service-connector register gcp-impersonate-sa --type gcp --auth-method impersonation --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core --target_principal=zenml-bucket-sl@zenml-core.iam.gserviceaccount.com --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl
```

{% code title="Example Command Output" %}
```text
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-impersonate-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠───────────────┼──────────────────────┨
┃ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

</details>

### Short-lived credentials

{% hint style="info" %}
This category of authentication methods uses temporary credentials explicitly configured in the Service Connector or generated by the Service Connector during auto-configuration. Of all available authentication methods, this is probably the least useful and you will likely never have to use it because it is terribly impractical: when short-lived credentials expire, Service Connectors become unusable and need to either be manually updated or replaced.

On the other hand, this authentication method is ideal if you're looking to grant someone else in your team temporary access to some resources without exposing your long-lived credentials.
{% endhint %}

A previous section described how [temporary credentials can be automatically generated from other, long-lived credentials](best-security-practices.md#generating-temporary-and-down-scoped-credentials) by most cloud provider Service Connectors. It only stands to reason that temporary credentials can also be generated manually by external means such as cloud provider CLIs and used directly to configure Service Connectors, or automatically generated during Service Connector auto-configuration.

This may be used as a way to grant an external party temporary access to some resources and have the Service Connector automatically become unusable (i.e. expire) after some time. Your long-lived credentials are kept safe, while the Service Connector only stores a short-lived credential.

<details>

<summary>AWS short-lived credentials auto-configuration example</summary>

The following is an example of using Service Connector auto-configuration to automatically generate a short-lived token from long-lived credentials configured for the local cloud provider CLI (AWS in this case):

```sh
AWS_PROFILE=connectors zenml service-connector register aws-sts-token --type aws --auto-configure --auth-method sts-token
```

{% code title="Example Command Output" %}
```text
⠸ Registering service connector 'aws-sts-token'...
Successfully registered service connector `aws-sts-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃     RESOURCE TYPE     │ RESOURCE NAMES                               ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃    🔶 aws-generic     │ us-east-1                                    ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃     📦 s3-bucket      │ s3://zenfiles                                ┃
┃                       │ s3://zenml-demos                             ┃
┃                       │ s3://zenml-generative-chat                   ┃
┃                       │ s3://zenml-public-datasets                   ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃ 🌀 kubernetes-cluster │ zenhacks-cluster                             ┃
┠───────────────────────┼──────────────────────────────────────────────┨
┃  🐳 docker-registry   │ 715803424590.dkr.ecr.us-east-1.amazonaws.com ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
{% endcode %}

The Service Connector is now configured with a short-lived token that will expire after some time. You can verify this by inspecting the Service Connector:

```sh
zenml service-connector describe aws-sts-token 
```

{% code title="Example Command Output" %}
```text
Service connector 'aws-sts-token' of type 'aws' with id '63e14350-6719-4255-b3f5-0539c8f7c303' is owned by user 'default' and is 'private'.
                        'aws-sts-token' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ e316bcb3-6659-467b-81e5-5ec25bfd36b0                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ NAME             │ aws-sts-token                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ TYPE             │ 🔶 aws                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ AUTH METHOD      │ sts-token                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE TYPES   │ 🔶 aws-generic, 📦 s3-bucket, 🌀 kubernetes-cluster, 🐳 docker-registry ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ RESOURCE NAME    │ <multiple>                                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SECRET ID        │ 971318c9-8db9-4297-967d-80cda070a121                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h58m17s                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-06-19 17:58:42.999323                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-06-19 17:58:42.999324                                              ┃
┗━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
            Configuration            
┏━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┓
┃ PROPERTY              │ VALUE     ┃
┠───────────────────────┼───────────┨
┃ region                │ us-east-1 ┃
┠───────────────────────┼───────────┨
┃ aws_access_key_id     │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_secret_access_key │ [HIDDEN]  ┃
┠───────────────────────┼───────────┨
┃ aws_session_token     │ [HIDDEN]  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┛
```
{% endcode %}

Note the temporary nature of the Service Connector. It will become unusable in 12 hours:

```sh
zenml service-connector list --name aws-sts-token 
```

{% code title="Example Command Output" %}
```text
┏━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME          │ ID                              │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼───────────────┼─────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-sts-token │ e316bcb3-6659-467b-81e5-5ec25bf │ 🔶 aws │ 🔶 aws-generic        │ <multiple>    │ ➖     │ default │ 11h57m12s  │        ┃
┃        │               │ d36b0                           │        │ 📦 s3-bucket          │               │        │         │            │        ┃
┃        │               │                                 │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │               │                                 │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```
{% endcode %}

</details>

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>
