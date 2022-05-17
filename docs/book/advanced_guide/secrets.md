---
description: ZenML provides functionality to store secrets locally and with AWS.
---

# Managing Secrets

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. You use secrets, for example, when connecting
to AWS, which requires an `access_key_id` and a `secret_access_key` which is
usually stored in your `~/.aws/credentials` file.

You might find you need to access those secrets from within your Kubernetes
cluster as it runs individual steps, or you might just want a centralized
location for the storage of secrets across your project. ZenML offers a basic
local secrets manager and an integration with the managed [AWS Secrets
Manager](https://aws.amazon.com/secrets-manager).

A ZenML Secret is a grouping of key-value pairs. These are accessed and
administered via the ZenML Secret Manager (a stack component).

Secrets are distinguished by having different schemas. An AWS SecretSchema, for
example, has key-value pairs for `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
as well as an optional `AWS_SESSION_TOKEN`. If you don't specify a schema at the
point of registration, ZenML will set the schema as `ArbitrarySecretSchema`, a kind
of default schema where things that aren't attached to a grouping can be stored.

## Registering a secrets manager

For early development purposes ZenML provides a local secrets manager which uses
a YAML file to store base64 encoded secret. If you want to instead use the AWS 
or GCP Secrets Manager as a non-local flavor that is also possible with ZenML.

To register a local secrets manager, use the CLI interface:

```shell
zenml secrets-manager register SECRETS_MANAGER_NAME --flavor=local
```

You will then need to add the secrets manager to a new stack that you register,
for example:

```shell
zenml stack register STACK_NAME \
    -m METADATA_STORE_NAME \
    -a ARTIFACT_STORE_NAME \
    -o ORCHESTRATOR_NAME \
    -x SECRETS_MANAGER_NAME
zenml stack set STACK_NAME
```

## Interacting with the Secrets Manager

A full guide on using the CLI interface to register, access, update and delete
secrets is available [here](https://apidocs.zenml.io/latest/cli/).

Note that there are two ways you can register or update your secrets. If you
wish to do so interactively, simply passing the secret name in as an argument
(as in the following example) will initiate an interactive process:

```shell
zenml secret register SECRET_NAME -i
```

If you wish to specify key-value pairs using command line arguments, you can do
so instead:

```shell
zenml secret register SECRET_NAME --key1=value1 --key2=value2
```

For secret values that are too big to pass as a command line argument, or have
special characters, you can also use the special `@` syntax to indicate to ZenML
that the value needs to be read from a file:

```bash
zenml secret register SECRET_NAME --attr_from_literal=value \
   --attr_from_file=@path/to/file.txt ...
```


## Using Secrets in a Kubeflow environment

ZenML will handle passing secrets down through the various stages of a Kubeflow
pipeline, so your secrets will be accessible wherever your code is running.

Note: The Secrets Manager as currently implemented does not work with our
Airflow orchestrator integration. [Let us know](https://zenml.io/slack-invite/)
if you would like us to prioritize adding this in!

To pass a particular secret as part of the environment available to a pipeline,
include a list of your secret names as an extra argument when you are defining
your pipeline, as in the following example (taken from the corresponding
Kubeflow example):

```python
from zenml.pipelines import pipeline
from zenml.integrations.constants import TENSORFLOW

@pipeline(required_integrations=[TENSORFLOW], secrets=["aws"], enable_cache=True)
def mnist_pipeline(
    importer,
    normalizer,
    trainer,
    evaluator,
):
    # Link all the steps together
    X_train, X_test, y_train, y_test = importer()
    X_trained_normed, X_test_normed = normalizer(X_train=X_train, X_test=X_test)
    model = trainer(X_train=X_trained_normed, y_train=y_train)
    evaluator(X_test=X_test_normed, y_test=y_test, model=model)
```

Secrets are made available to steps regardless of whether you're using a local
secret store or non-local AWS/GCP Secrets Manager.

## Using the AWS Secrets Manager integration

Amazon offers a managed secrets manager to store and use secrets for AWS 
services. If your stack is primarily running on AWS, you can use our integration 
to interact with it. 
Before getting started with the aws secret manager you'll need to make sure to
have your aws credential set up locally and you have access to a service account
with read/write permissions to the secrets manager. 
[This](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html)
guide can help you get started. 

With this set up, using the 
[AWS Secrets Manager](https://aws.amazon.com/secrets-manager) is just as easy as 
using the local version. Make sure that the integration is installed first, and
then register your secrets manager in the following way:

```shell
zenml integration install aws
zenml secrets-manager register AWS_SECRETS_MANAGER_NAME --flavor=aws
```

If you are using the [ZenML Kubeflow
integration](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow) for
your orchestrator, you can then access the keys and their corresponding values
for all the secrets you imported in the pipeline definition (as mentioned
above). The keys that you used when creating the secret will be capitalized when
they are passed down into the images used by Kubeflow. For example, in the case
of accessing the `aws` secret referenced above, you would get the value for the
`aws_secret_access_key` key with the following code (within a step):

```python
import os

os.environ.get('AWS_SECRET_ACCESS_KEY')
```

Note that some secrets will get used by your stack implicitly. For
example, in the case of when you are using an AWS S3 artifact store, the
environment variables passed down will be used to confirm access.

## Using the GCP Secret Manager
Google offers a managed secret manager to store and use secrets for GCP 
services. If your stack is primarily running on GCP, you can use our integration 
to interact with it. 

Before getting started with the aws secret manager you'll need to make sure to
have your aws credential set up locally, and you have access to a service account
with read/write permissions to the secrets manager. 
[This](https://cloud.google.com/sdk/docs/install-sdk) guide can help you 
get started. 

With this set up, using the 
[GCP Secret Manager](https://cloud.google.com/secret-manager) is just as easy as 
using the local version. Make sure that the integration is installed first, and
then register your secrets manager in the following way:

```shell
zenml integration install gcp_secrets_manager
zenml secrets-manager register GCP_SECRETS_MANAGER_NAME -t gcp \ 
    --project_id=<ID_OF_YOUR_PROJECT>
```

The Project ID refers to the GCP project of your secrets manager. 
[This](https://support.google.com/googleapi/answer/7014113?hl=en) is how you
can find the project ID of your project.

If you are using the [ZenML Kubeflow
integration](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow) for
your orchestrator, you can then access the keys and their corresponding values
for all the secrets you imported in the pipeline definition (as mentioned
above). The keys that you used when creating the secret will be capitalized when
they are passed down into the images used by Kubeflow. For example, in the case
of accessing the `aws` secret referenced above, you would get the value for the
`aws_secret_access_key` key with the following code (within a step):

```python
import os 

os.environ.get('AWS_SECRET_ACCESS_KEY')
```

Note that some secrets will get used by your stack implicitly. For
example, in the case of when you are using an AWS S3 artifact store, the
environment variables passed down will be used to confirm access.
