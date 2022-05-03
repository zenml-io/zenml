# 🔑 Managing Secrets with AWS Secret Manager

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. A
ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Manager (a stack component).

## 🗺 Overview

The example pipeline is simple as can be. In our one and only step we access the
stacks active secret manager and
query for a secret called `example_secret`. We then access the value for the
unique key: `example_secret_key` of this secret.

Similarly, you would be able to pass access keys, password, credentials and so
on into your pipeline steps to do with as
you please.

# 🖥 Run it locally

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML:

```shell
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install aws

# pull example
zenml example pull aws_secret_manager
cd zenml_examples/aws_secret_manager

# Initialize ZenML repo
zenml init
```

### 🥞 Set up your stack

To get going with aws make sure to have your aws credential set up locally. We
recommend this
[guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html)
to make sure everything is
set up properly.

```shell
zenml secrets-manager register aws_secrets_manager --flavor aws
zenml stack register secrets_stack -m default -o default -a default -x aws_secrets_manager
zenml stack set secrets_stack
```

In case you run into issues here, feel free to use a local secret manager. Just
replace `-t aws` with `-t local` to
revert to a local version of a secret manager.

### Create a secret

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

Our docs regarding the aws secrets manager and secrets in general can be found
[here](https://docs.zenml.io/advanced-guide/integrations/secrets). You'll also 
find more information on secrets managers in our docs on the 
[stack component](https://docs.zenml.io/stack-components/secrets_manager).


We also have extensive CLI docs for the
[secret manager](https://apidocs.zenml.io/0.7.1/cli/#zenml.cli--setting-up-a-secrets-manager)
and the
[secrets](https://apidocs.zenml.io/0.7.1/cli/#zenml.cli--using-secrets).

