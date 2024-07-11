---
description: Seamlessly register a cloud stack using existing infrastructure
---

# Register a cloud stack with existing infrastructure

In ZenML, the [stack](../../user-guide/production-guide/understand-stacks.md) 
is a fundamental concept that represents the configuration of your 
infrastructure. In a normal workflow, creating a stack requires you to first 
deploy the necessary pieces of infrastructure and then define them as stack 
components in ZenML with proper authentication.

Especially in a remote setting, this process can be challenging and 
time-consuming, and it may create multi-faceted problems. This is why we 
implemented a feature called the stack wizard, that allows you to **browse 
through your existing infrastructure and use it to register a ZenML cloud 
stack**.

{% hint style="info" %}
If you do not have the required infrastructure pieces already deployed
on your cloud, you can also use [the 1-click deployment tool to build your 
cloud stack](deploy-a-cloud-stack.md).
{% endhint %}

# How to use the Stack Wizard?

At the moment, the stack wizard can only be accessed through our CLI.

{% tabs %}
{% tab title="CLI" %}

In order to register a remote stack over the CLI with the stack wizard,
you can use the following command:

```shell
zenml stack register <STACK_NAME> -p {aws|gcp}
```

To register the cloud stack, the first thing that the wizard needs is a service 
connector. You can either use an existing connector by providing its ID or name 
`-sc <SERVICE_CONNECTOR_ID_OR_NAME>` or the wizard will create one for you.

Similar to the service connector, you can also use existing stack components.
However, this is only possible if these components are already configured with 
the same service connector that you provided through the parameter 
described above.

{% hint style="warning" %}
Currently, the stack wizard only works on AWS and GCP. We are working on bringing 
support to Azure as well. Stay in touch for further updates.
{% endhint %}

### AWS

If you select `aws` as your cloud provider, and you haven't selected a connector
yet, you will be prompted to select an authentication method for your stack.

{% code title="Example Command Output" %}
```
                         Available authentication methods for aws                                      
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Choice ┃ Name                 ┃ Required                                       ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ [0]    │ AWS Secret Key       │ aws_access_key_id  (AWS Access Key ID)         │
│        │                      │ aws_secret_access_key  (AWS Secret Access Key) │
│        │                      │ region  (AWS Region)                           │
│        │                      │                                                │
├────────┼──────────────────────┼────────────────────────────────────────────────┤
│ [1]    │ AWS STS Token        │ aws_access_key_id  (AWS Access Key ID)         │
│        │                      │ aws_secret_access_key  (AWS Secret Access Key) │
│        │                      │ aws_session_token  (AWS Session Token)         │
│        │                      │ region  (AWS Region)                           │
│        │                      │                                                │
├────────┼──────────────────────┼────────────────────────────────────────────────┤
│ [2]    │ AWS IAM Role         │ aws_access_key_id  (AWS Access Key ID)         │
│        │                      │ aws_secret_access_key  (AWS Secret Access Key) │
│        │                      │ region  (AWS Region)                           │
│        │                      │ role_arn  (AWS IAM Role ARN)                   │
│        │                      │                                                │
├────────┼──────────────────────┼────────────────────────────────────────────────┤
│ [3]    │ AWS Session Token    │ aws_access_key_id  (AWS Access Key ID)         │
│        │                      │ aws_secret_access_key  (AWS Secret Access Key) │
│        │                      │ region  (AWS Region)                           │
│        │                      │                                                │
├────────┼──────────────────────┼────────────────────────────────────────────────┤
│ [4]    │ AWS Federation Token │ aws_access_key_id  (AWS Access Key ID)         │
│        │                      │ aws_secret_access_key  (AWS Secret Access Key) │
│        │                      │ region  (AWS Region)                           │
│        │                      │                                                │
└────────┴──────────────────────┴────────────────────────────────────────────────┘
```
{% endcode %}

Based on your selection, you will have to provide the required parameters listed 
above. This will allow ZenML to create a Service Connector and 
authenticate you to use your cloud resources.

Next, for each missing component, the available resources will be listed to 
you as follows:

{% code title="Example Command Output for Artifact Stores" %}
```
                       Available AWS storages                                                           
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Choice ┃ Storage                                                     ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ [0]    │ s3://**************                                         │
├────────┼─────────────────────────────────────────────────────────────┤
│ [1]    │ s3://**************                                         │
└────────┴─────────────────────────────────────────────────────────────┘
```
{% endcode %}

### GCP

If you select `gcp` as your cloud provider, and you haven't selected a connector
yet, you will be prompted to select an authentication method for your stack.

{% code title="Example Command Output" %}
```
                    Available authentication methods for gcp                                                                                           
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Choice ┃ Name                 ┃ Required                                          ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ [0]    │ GCP User Account     │ user_account_json  (GCP User Account Credentials  │
│        │                      │       JSON optionally base64 encoded.)            │
│        │                      │ project_id  (GCP Project ID where the target      │
│        │                      │       resource is located.)                       │
│        │                      │                                                   │
├────────┼──────────────────────┼───────────────────────────────────────────────────┤
│ [1]    │ GCP Service Account  │ service_account_json  (GCP Service Account Key    │
│        │                      │       JSON optionally base64 encoded.)            │
│        │                      │                                                   │
├────────┼──────────────────────┼───────────────────────────────────────────────────┤
│ [2]    │ GCP External Account │ external_account_json  (GCP External Account      │
│        │                      │       JSON optionally base64 encoded.)            │
│        │                      │ project_id  (GCP Project ID where the target      │
│        │                      │       resource is located.)                       │ 
│        │                      │                                                   │
├────────┼──────────────────────┼───────────────────────────────────────────────────┤
│ [3]    │ GCP Oauth 2.0 Token  │ token  (GCP OAuth 2.0 Token)                      │
│        │                      │ project_id  (GCP Project ID where the target      │
│        │                      │       resource is located.)                       │
│        │                      │                                                   │
├────────┼──────────────────────┼───────────────────────────────────────────────────┤
│ [4]    │ GCP Service Account  │ service_account_json  (GCP Service Account Key    │
│        │                      │       JSON optionally base64 encoded.)            │
│        │ Impersonation        │ target_principal  (GCP Service Account Email to   │
│        │                      │       impersonate)                                │
│        │                      │                                                   │
└────────┴──────────────────────┴───────────────────────────────────────────────────┘
```
{% endcode %}

Based on your selection, you will have to provide the required parameters listed 
above. This will allow ZenML to create a Service Connector and 
authenticate you to use your cloud resources.

Next, for each missing component, the available resources will be listed to 
you as follows:

{% code title="Example Command Output for Artifact Stores" %}
```
        Available GCP storages                                                                                                   
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Choice  ┃ Storage               ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ [0]     │ gs://**************   │
├─────────┼───────────────────────┤
│ [1]     │ gs://**************   │
└─────────┴───────────────────────┘
```
{% endcode %}

Based on your selection, ZenML will create the stack component and ultimately 
register the stack for you.

{% endtab %}

{% tab title="Dashboard" %}

We are working hard to bring this feature to our dashboard as well. Stay in 
touch for further updates.

{% endtab %}
{% endtabs %}

There you have it! Through the wizard, you just registered a cloud stack 
and, you can start running your pipelines on a remote setting.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
