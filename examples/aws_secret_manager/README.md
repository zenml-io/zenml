# 🔑 Managing Secrets with AWS Secret Manager

## 🗺 Overview


## 🧰 How the example is implemented

# 🖥 Run it locally

## ⏩ SuperQuick `aws_secret_manager` run

If you're really in a hurry, and you want just to see this example pipeline run,
without wanting to fiddle around with all the individual installation and
configuration steps, just run the following:

```shell
zenml example run aws_secret_manager
```

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

To get going with aws make sure to have your aws credential set up locally. We recommend this 
[guide](https://docs.aws.amazon.com/sdk-for-java/v1/developer-guide/setup-credentials.html) to make sure everything is
set up properly.

```shell
zenml secrets-manager register aws_secrets_manager -t aws
zenml stack register secrets_stack -m default -o default -a default -x aws_secrets_manager
zenml stack set secrets_stack
```

In case you run into issues here, feel free to use a local secret manager. Just replace `-t aws` with `-t local` to 
revert to a local version of a secret manager.

### Create a secret

Here we are creating a secret called `example_secret` which contains a single key-value pair:
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
In order to clean up, delete the remaining ZenML references.

```shell
rm -rf zenml_examples
```

# 📜 Learn more

Our docs regarding the aws secret manager and secrets in general can be found 
[here](https://docs.zenml.io/features/secrets).
