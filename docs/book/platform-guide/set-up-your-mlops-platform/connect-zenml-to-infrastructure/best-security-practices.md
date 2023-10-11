---
description: >-
  Best practices concerning the various authentication methods implemented by
  Service Connectors.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


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

In some cases, this method may also be perceived as a security risk, because it can give access to the same resources and services that the ZenML Server itself uses for its internals, which should be kept separate from the actual users and ML workloads.
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

* when used with a local ZenML deployment, like the default deployment, or [a local ZenML server started with `zenml up`](../../../user-guide/starter-guide/connect-to-a-deployed-zenml.md), the implicit authentication method will use the configuration files and credentials or environment variables set up _on your local machine_. These will not be available to anyone else outside your local environment and will also not be accessible to workloads running in other environments on your local host. This includes for example local K3D Kubernetes clusters and local Docker containers.
* when used with a remote ZenML server, the implicit authentication method only works if your ZenML server is deployed in the same cloud as the one supported by the Service Connector Type that you are using. For instance, if you're using the AWS Service Connector Type, then the ZenML server must also be deployed in AWS (e.g. in an EKS Kubernetes cluster). You may also need to manually adjust the cloud configuration of the remote cloud workload where the ZenML server is running to allow access to resources (e.g. add permissions to the AWS IAM role attached to the EC2 or EKS node, add roles to the GCP service account attached to the GKE cluster nodes).

<details>

<summary>GCP implicit authentication method example</summary>

The following is an example of using the GCP Service Connector's implicit authentication method to gain immediate access to all the GCP resources that the ZenML server also has access to. Note that this is only possible because the ZenML server is also deployed in GCP, in a GKE cluster, and the cluster is attached to a GCP service account with permissions to access the project resources:

```
$ zenml service-connector register gcp-implicit --type gcp --auth-method implicit --project_id=zenml-core
Successfully registered service connector `gcp-implicit` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 gcs-bucket         │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type gcs-bucket
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                                  ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────┼─────────────────────────────────────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 📦 gcs-bucket │ gs://annotation-gcp-store                       ┃
┃                                      │                │                │               │ gs://zenml-bucket-sl                            ┃
┃                                      │                │                │               │ gs://zenml-kubeflow-artifact-store              ┃
┃                                      │                │                │               │ gs://zenml-project-time-series-bucket           ┃
┃                                      │                │                │               │ gs://zenml-public-bucket                        ┃
┃                                      │                │                │               │ gs://zenml-vertex-test                          ┃
┃                                      │                │                │               │ gs://zenml_projects_artifact_store              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type kubernetes-cluster
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES     ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🌀 kubernetes-cluster │ zenml-test-cluster ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-implicit --resource-type docker-registry
Service connector 'gcp-implicit' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE      │ RESOURCE NAMES    ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼────────────────────┼───────────────────┨
┃ 0e244dd6-6f0a-4e63-ae79-33f8d6d6f8f9 │ gcp-implicit   │ 🔵 gcp         │ 🐳 docker-registry │ gcr.io/zenml-core ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━┛
```

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

The following example shows the difference between the long-lived AWS credentials configured for an AWS Service Connector and kept on the ZenML server and the temporary Kubernetes API token credentials that the client receives and uses to access the resource. Note the expiration time on the Kubernetes API token:

```
$ zenml service-connector describe eks-zenhacks-cluster
Service connector 'eks-zenhacks-cluster' of type 'aws' with id '7365b136-65b2-4a88-8283-9ecaefbe812b' is owned by user 'default' and is 'private'.
   'eks-zenhacks-cluster' aws Service Connector Details    
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                ┃
┠──────────────────┼──────────────────────────────────────┨
┃ ID               │ 7365b136-65b2-4a88-8283-9ecaefbe812b ┃
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
┃ SECRET ID        │ 735c0e1a-cf1e-4a43-aed0-144b9a61c903 ┃
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
┃ CREATED_AT       │ 2023-05-17 14:33:06.173039           ┃
┠──────────────────┼──────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-17 14:33:06.173041           ┃
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

$ zenml service-connector describe eks-zenhacks-cluster --client
Service connector 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' of type 'kubernetes' with id '7365b136-65b2-4a88-8283-9ecaefbe812b' is owned by user 'default' and is 
'private'.
 'eks-zenhacks-cluster (kubernetes-cluster | zenhacks-cluster client)' kubernetes Service 
                                    Connector Details                                     
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ ID               │ 7365b136-65b2-4a88-8283-9ecaefbe812b                                ┃
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
┃ EXPIRES IN       │ 11h59m56s                                                           ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                             ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                  ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-17 14:33:41.861267                                          ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-17 14:33:41.861269                                          ┃
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

</details>

_**Issuing downscoped credentials**_: in addition to the above, some authentication methods also support restricting the generated temporary API tokens to the minimum set of permissions required to access the target resource or set of resources. This is currently available for the AWS Service Connector's "Federation Token" and "IAM Role" authentication methods.

<details>

<summary>AWS down-scoped credentials example</summary>

It's not easy to showcase this without using some ZenML Python Client code, but here is an example that proves that the AWS client token issued to an S3 client can only access the S3 bucket resource it was issued for, even if the originating AWS Service Connector is able to access multiple S3 buckets with the corresponding long-lived credentials:

```
$ zenml service-connector register aws-federation-multi --type aws --auth-method=federation-token --auto-configure 
⠴ Registering service connector 'aws-federation-multi'...
Successfully registered service connector `aws-federation-multi` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 88b82bbe-bf35-4fbe-8805-217121c133c9 │ aws-federation-multi │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                      │                │ 📦 s3-bucket          │                ┃
┃                                      │                      │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                      │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify aws-federation-multi --resource-type s3-bucket
Service connector 'aws-federation-multi' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME       │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES                        ┃
┠──────────────────────────────────────┼──────────────────────┼────────────────┼───────────────┼───────────────────────────────────────┨
┃ 88b82bbe-bf35-4fbe-8805-217121c133c9 │ aws-federation-multi │ 🔶 aws         │ 📦 s3-bucket  │ s3://public-flavor-logos              ┃
┃                                      │                      │                │               │ s3://zenbytes-bucket                  ┃
┃                                      │                      │                │               │ s3://zenfiles                         ┃
┃                                      │                      │                │               │ s3://zenml-demos                      ┃
┃                                      │                      │                │               │ s3://zenml-generative-chat            ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

# The next part involves running some ZenML Python code

$ python
>>> from zenml.client import Client
>>> client = Client()
>>>
>>> # Get a Service Connector client for a particular S3 bucket
>>> connector_client = client.get_service_connector_client(name_id_or_prefix="aws-federation-multi", resource_type="s3-bucket", resource_id="s3://zenfiles")
>>>
>>> # Get the S3 boto3 python client pre-configured and pre-authenticated
>>> # from the Service Connector client
>>> s3_client = connector_client.connect()
>>>
>>> # Verify access to the chosen S3 bucket using the temporary token that
>>> # was issued to the client.
>>> s3_client.head_bucket(Bucket="zenfiles")
{'ResponseMetadata': {'HTTPStatusCode': 200, ...}}
>>>
>>> # Try to access another S3 bucket that the original AWS long-lived credentials can access.
>>> # An error will be thrown indicating that the bucket is not accessible.
>>> s3_client.head_bucket(Bucket="zenml-demos")
╭─────────────────────────────── Traceback (most recent call last) ────────────────────────────────╮
│ <stdin>:1 in <module>                                                                            │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:530 in        │
│ _api_call                                                                                        │
│                                                                                                  │
│    527 │   │   │   │   │   f"{py_operation_name}() only accepts keyword arguments."              │
│    528 │   │   │   │   )                                                                         │
│    529 │   │   │   # The "self" in this scope is referring to the BaseClient.                    │
│ ❱  530 │   │   │   return self._make_api_call(operation_name, kwargs)                            │
│    531 │   │                                                                                     │
│    532 │   │   _api_call.__name__ = str(py_operation_name)                                       │
│    533                                                                                           │
│                                                                                                  │
│ /home/stefan/aspyre/src/zenml/.venv/lib/python3.8/site-packages/botocore/client.py:964 in        │
│ _make_api_call                                                                                   │
│                                                                                                  │
│    961 │   │   if http.status_code >= 300:                                                       │
│    962 │   │   │   error_code = parsed_response.get("Error", {}).get("Code")                     │
│    963 │   │   │   error_class = self.exceptions.from_code(error_code)                           │
│ ❱  964 │   │   │   raise error_class(parsed_response, operation_name)                            │
│    965 │   │   else:                                                                             │
│    966 │   │   │   return parsed_response                                                        │
│    967                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
ClientError: An error occurred (403) when calling the HeadBucket operation: Forbidden
```

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

```
$ zenml service-connector register gcp-empty-sa --type gcp --auth-method service-account --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-empty-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ db967769-4cd5-4f07-a3f4-54e3fe534d88 │ gcp-empty-sa   │ 🔵 gcp         │ 🔵 gcp-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 gcs-bucket         │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-empty-sa --resource-type kubernetes-cluster
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: Failed to list GKE clusters:
403 Required "container.clusters.list" permission(s) for "projects/20219041791".

$ zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to list GCS buckets:
403 GET https://storage.googleapis.com/storage/v1/b?project=zenml-core&projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.list access to the Google Cloud project.
Permission 'storage.buckets.list' denied on resource (or it may not exist).

$ zenml service-connector verify gcp-empty-sa --resource-type gcs-bucket --resource-id zenml-bucket-sl
Error: Service connector 'gcp-empty-sa' verification failed: connector authorization failure: failed to fetch GCS bucket
zenml-bucket-sl: 403 GET https://storage.googleapis.com/storage/v1/b/zenml-bucket-sl?projection=noAcl&prettyPrint=false:
empty-connectors@zenml-core.iam.gserviceaccount.com does not have storage.buckets.get access to the Google Cloud Storage bucket.
Permission 'storage.buckets.get' denied on resource (or it may not exist).

```

Next, we'll register a GCP Service Connector that actually uses account impersonation to access the `zenml-bucket-sl` GCS bucket and verify that it can actually access the bucket:

```
$ zenml service-connector register gcp-impersonate-sa --type gcp --auth-method impersonation --service_account_json=@empty-connectors@zenml-core.json  --project_id=zenml-core --target_principal=zenml-bucket-sl@zenml-core.iam.gserviceaccount.com --resource-type gcs-bucket --resource-id gs://zenml-bucket-sl
Expanding argument value service_account_json to contents of file /home/stefan/aspyre/src/zenml/empty-connectors@zenml-core.json.
Successfully registered service connector `gcp-impersonate-sa` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ f586c28e-3d60-4be5-8961-853592c48e41 │ gcp-impersonate-sa │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛

$ zenml service-connector verify gcp-impersonate-sa --resource-type gcs-bucket --resource-id zenml-bucket-sl
Service connector 'gcp-impersonate-sa' is correctly configured with valid credentials and has access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME     │ CONNECTOR TYPE │ RESOURCE TYPE │ RESOURCE NAMES       ┃
┠──────────────────────────────────────┼────────────────────┼────────────────┼───────────────┼──────────────────────┨
┃ f586c28e-3d60-4be5-8961-853592c48e41 │ gcp-impersonate-sa │ 🔵 gcp         │ 📦 gcs-bucket │ gs://zenml-bucket-sl ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━┛
```

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

```
$ AWS_PROFILE=connectors zenml service-connector register aws-sts-token --type aws --auto-configure --auth-method sts-token
⠸ Registering service connector 'aws-sts-token'...
Successfully registered service connector `aws-sts-token` with access to the following resources:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┓
┃             CONNECTOR ID             │ CONNECTOR NAME │ CONNECTOR TYPE │ RESOURCE TYPE         │ RESOURCE NAMES ┃
┠──────────────────────────────────────┼────────────────┼────────────────┼───────────────────────┼────────────────┨
┃ 63e14350-6719-4255-b3f5-0539c8f7c303 │ aws-sts-token  │ 🔶 aws         │ 🔶 aws-generic        │ 🤷 none listed ┃
┃                                      │                │                │ 📦 s3-bucket          │                ┃
┃                                      │                │                │ 🌀 kubernetes-cluster │                ┃
┃                                      │                │                │ 🐳 docker-registry    │                ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┛

$ zenml service-connector describe aws-sts-token 
Service connector 'aws-sts-token' of type 'aws' with id '63e14350-6719-4255-b3f5-0539c8f7c303' is owned by user 'default' and is 'private'.
                        'aws-sts-token' aws Service Connector Details                         
┏━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ PROPERTY         │ VALUE                                                                   ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ ID               │ 63e14350-6719-4255-b3f5-0539c8f7c303                                    ┃
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
┃ SECRET ID        │ ff93e6a0-2ce2-42ce-a540-1b88d26d0988                                    ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SESSION DURATION │ N/A                                                                     ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ EXPIRES IN       │ 11h59m55s                                                               ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ OWNER            │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ WORKSPACE        │ default                                                                 ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ SHARED           │ ➖                                                                      ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ CREATED_AT       │ 2023-05-19 08:58:09.755925                                              ┃
┠──────────────────┼─────────────────────────────────────────────────────────────────────────┨
┃ UPDATED_AT       │ 2023-05-19 08:58:09.755927                                              ┃
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

Note the temporary nature of the Service Connector. It will become unusable in 12 hours:

```
$ zenml service-connector list --name aws-sts-token 
┏━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━┓
┃ ACTIVE │ NAME          │ ID                                   │ TYPE   │ RESOURCE TYPES        │ RESOURCE NAME │ SHARED │ OWNER   │ EXPIRES IN │ LABELS ┃
┠────────┼───────────────┼──────────────────────────────────────┼────────┼───────────────────────┼───────────────┼────────┼─────────┼────────────┼────────┨
┃        │ aws-sts-token │ 63e14350-6719-4255-b3f5-0539c8f7c303 │ 🔶 aws │ 🔶 aws-generic        │ <multiple>    │ ➖     │ default │ 11h59m50s  │        ┃
┃        │               │                                      │        │ 📦 s3-bucket          │               │        │         │            │        ┃
┃        │               │                                      │        │ 🌀 kubernetes-cluster │               │        │         │            │        ┃
┃        │               │                                      │        │ 🐳 docker-registry    │               │        │         │            │        ┃
┗━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━┛
```

</details>
