---
description: Use secrets across your ZenML pipeline.
---
# Secrets Manager

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. For example, you'll use secrets to connecting 
to AWS, which requires an `access_key_id` and a `secret_access_key`. On your 
local machine this is usually stored in your `~/.aws/credentials` file.
You might find you need to access those secrets from within your Kubernetes
cluster as it runs individual steps. You might also just want a centralized 
location for the storage of secrets across your ZenML project. ZenML gives you
all this with the Secret Manager stack component.


## CLI

Check out the CLI commands concerning the secrets manager
[here](https://apidocs.zenml.io/latest/cli/#zenml.cli--setting-up-a-secrets-manager)
. This will help you set up the secrets manager as a stack component. 

Once you have the stack component set up in your active stack, you'll be able to
interact with it using the `secrets` CLI group. You'll find the corresponding
CLI docs [here](https://apidocs.zenml.io/latest/cli/#zenml.cli--using-secrets)

## Implementations


{% tabs %}
{% tab title="Local Secrets Manager " %}

The local secrets manager is mainly built for the purpose of quickly getting 
started with secrets outside any production setting. When using this secret 
manager the secrets are store in your 
[global zenml config](../developer-guide/repo-and-config.md#config). 

{% hint style="warning" %}
The secrets will be saved base64 encoded without any encryption. 
This offers **no** security benefits. Anyone with access to your machine will
have unrestricted access to these.
{% endhint %}
{% endtab %}

{% tab title="AWS Secrets Manager" %}

The Integration of the [AWS Secrets Manager](Southernlights#1942) gives you a
direct interface to your Secrets stored on AWS.

### Prerequisites

In order to use the secret manager you will need to have an AWS organization 
with a secrets manager. Additionally, you will need to have at least read access
to this secrets manager with your account or through a service principal.

You will have to set up the CLI SDK on your local machine. We recommend this
[guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html)
to get started.

### Setting up the Stack Component

* flavor - aws
* region_name - default us-east-1

### Good to Know

WIP

{% endtab %}

{% tab title="GCP Secret Manager" %}

### Prerequisites

WIP

### Setting up the Stack Component

* flavor - aws
* project_id - 

### Good to Know

The Google Secret Manager considers a single key-value pair to be a secret. Within ZenML and other
Integrations like the AWS Secret Manager a Secret is a collection of key-value pairs.
An example for this would be a secret that contains username and password:

login_secret = {'username': 'aria', 'password': 'somepwd'}

In order to map this concept onto the GCP Secret Manager, ZenML uses labels and prepended group_keys.
The example from above will show up in the GCP UI like this:

[TODO]([GET_Screenshot])

Note: 'login_secret_username' and 'login_secret_password' represent the two key-value pairs associated
with the 'login_secret'.

{% endtab %}
{% endtabs %}

## Build Your Own

WIP
