# 🔑 Managing Secrets with AWS/GCP Secret Manager

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. A
ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Manager (a stack component).

## 🗺 Overview

The example pipeline is simple as can be. In our one and only step we access the
stacks active secret manager and
query for an example called `example_secret`. We then access the contents of
this secret and query the secret with the
unique key: `example_secret_key`.

Similarly, you would be able to pass access keys, password, credentials and so
on into your pipeline steps to do with as
you please.

# 🖥 Run it locally

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML. Within 
this example You'll be able to choose between using the
local yaml based secrets manager, 
the [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) 
and the [GCP Secret Manager](https://cloud.google.com/secret-manager).:

```shell
# install CLI
pip install zenml

# either install the aws integrations
zenml integration install aws

# or alternatively the gcp integration
zenml integration install gcp_secrets_manager

# pull example
zenml example pull cloud_secrets_manager
cd zenml_examples/cloud_secrets_manager

# Initialize ZenML repo
zenml init
```

### 🥞 Set up your stack for AWS

To get going with aws make sure to have your aws credential set up locally. We
recommend this
[guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html)
to make sure everything is
set up properly.

```shell
zenml secrets-manager register aws_secrets_manager -t aws
zenml stack register secrets_stack -m default -o default -a default -x aws_secrets_manager
zenml stack set aws_secrets_stack
```

### 🥞 Set up your stack for GCP

To get going with gcp make sure to have gcloud set up locally with a user or 
ideally a service account with permissions to access the secret manager. 
[This](https://cloud.google.com/sdk/docs/install-sdk) guide should help you get 
started. Once everything is set up on your machine, make sure to enable the 
secrets manager API within your gcp project.

```shell
zenml secrets-manager register gcp_secrets_manager -t gcp_secrets_manager
zenml stack register secrets_stack -m default -o default -a default -x gcp_secrets_manager
zenml stack set gcp_secrets_stack
```

### Or stay on a local stack

In case you run into issues with either of the glouds, feel free to use a local 
secret manager. Just replace `-t aws`/`-t gcp_secret_manager` with `-t local` to
use a local file based version of a secret manager. Be aware that this is not 
a recommended location to store sensitive information.


### 🤫 Create a secret

Here we are creating a secret called `example_secret` which contains a single
key-value pair:
{example_secret_key: example_secret_value}

```shell
zenml secret register example_secret -k example_secret_key -v example_secret_value
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the example secret:

```shell
  zenml secret delete example_secret -k example_secret_key -v example_secret_value
```

and the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the aws secret manager and secrets in general can be found
[here](https://docs.zenml.io/features/secrets).

We also have extensive CLI docs for the
[secret manager](https://apidocs.zenml.io/0.7.1/cli/#zenml.cli--setting-up-a-secrets-manager)
and the
[secrets](https://apidocs.zenml.io/0.7.1/cli/#zenml.cli--using-secrets).
