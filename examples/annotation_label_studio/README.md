# 🏷 Continuous Annotation with Label Studio

Data annotation / labelling is a core part of MLOps that is frequently left out
of the conversation. ZenML offers a way to build continuous annotation (combining
training and annotation into a loop) with Label Studio. This uses a combination
of user-defined steps as well as some built-in steps that ZenML provides.

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

In order to run this example, you need to install and initialize ZenML.

```shell
# install CLI
pip install zenml

# pull example
zenml example pull annotation_label_studio
cd zenml_examples/annotation_label_studio

# Initialize ZenML repo
zenml init
```

### 🥞 Set up your stack for Microsoft Azure

To get going with aws make sure to have your aws credential set up locally. We
recommend this
[guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html)
to make sure everything is
set up properly.

```shell
zenml integration install azure

zenml secrets-manager register aws_secrets_manager --flavor=aws
zenml stack register secrets_stack -m default -o default -a default -x aws_secrets_manager --set
```

### 🥞 Set up your stack for GCP

To get going with gcp make sure to have gcloud set up locally with a user or 
ideally a service account with permissions to access the secret manager. 
[This](https://cloud.google.com/sdk/docs/install-sdk) guide should help you get 
started. Once everything is set up on your machine, make sure to enable the 
secrets manager API within your GCP project. You will need to create a project
and get the `project_id` which will need to be specified when you register the
secrets manager.

```shell
zenml integration install gcp

zenml secrets-manager register gcp_secrets_manager --flavor=gcp_secrets_manager --project_id=PROJECT_ID
zenml stack register secrets_stack -m default -o default -a default -x gcp_secrets_manager --set
```

### 🥞 Set up your stack for Azure

To get going with Azure you will need to install and configure the 
[Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
with the correct credentials to access the Azure secrets manager.

```shell
zenml integration install azure

zenml secrets-manager register azure_key_vault --flavor=azure_key_vault --key_vault_name=<VAULT-NAME>
zenml stack register secrets_stack -m default -o default -a default -x azure_key_vault --set
```


### 🤫 Create a secret

Here we are creating a secret called `example_secret` which contains a single
key-value pair:
{example_secret_key: example_secret_value}

```shell
zenml secret register example_secret --example_secret_key=example_secret_value
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

Alternatively, if you want to run based on the config.yaml you can run with:

```bash
zenml pipeline run pipelines/secret_loading_pipeline/secret_loading_pipeline.py -c config.yaml 
```

### 🧽 Clean up

In order to clean up, delete the example secret:

```shell
  zenml secret delete annotation_label_studio
```

and the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

If you want to learn more about annotation in general or about how to use your
own annotation tool in ZenML
check out our [docs](https://docs.zenml.io/extending-zenml/secrets-managers).

We also have extensive CLI docs for the
[secret manager](https://apidocs.zenml.io/latest/cli/#zenml.cli--setting-up-a-secrets-manager)
and the
[secrets](https://apidocs.zenml.io/latest/cli/#zenml.cli--using-secrets).
