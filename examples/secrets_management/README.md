# 🔑 Managing Secrets with ZenML

Most projects involving either cloud infrastructure or of a certain complexity
will involve secrets of some kind. A ZenML Secret is a grouping of key-value
pairs. These are accessed and administered via the ZenML Secrets Store.

## 🗺 Overview

The example pipeline is simple as can be. In our one and only step we access the
ZenML secrets store and query for a sample secret called `example-secret`. We
then access the contents of this secret and look for the secret value with the
unique key: `example_secret_key`.

Similar to what is shown here, you would be able to pass access keys, passwords,
credentials and so on into your pipeline steps to do with as you please.

# 🖥 Run it locally

## 👣 Step-by-Step

### 📄 Prerequisites

In order to run this example, you need to install and initialize ZenML. ZenML
already comes with a default Secrets Store that saves secrets in the same
database used to store the other ZenML core concepts and metadata (Stacks,
Stack Components etc.).


```shell
# install CLI
pip install "zenml[server]"

# pull example
zenml example pull secrets_management
cd zenml_examples/secrets_management

# Initialize ZenML repo
zenml init

# Start the ZenServer to enable dashboard access
zenml up
```

### 🤫 Create a secret

Here we are creating a secret called `example-secret` which contains a single
key-value pair: `{example_secret_key: example_secret_value}`. We'll access this
secret in the pipeline step.

```shell
zenml secret create example-secret --example_secret_key=example_secret_value
```

### ▶️ Run the Code

Now we're ready. Execute:

```bash
python run.py
```

### 🧽 Clean up

In order to clean up, delete the example secret:

```shell
zenml secret delete example-secret
```

and the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

If you want to learn more about centralized secrets management with ZenML in
general or about how to build your own secrets store back-end, check out our
[docs](https://docs.zenml.io/platform-guide/set-up-your-mlops-platform/use-the-secret-store).

We also have extensive docs for the
[secrets CLI](https://apidocs.zenml.io/latest/cli/#zenml.cli--secrets-management).
