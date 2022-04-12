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
zenml integration install s3

# pull example
zenml example pull aws_secret_manager
cd zenml_examples/aws_secret_manager

# Initialize ZenML repo
zenml init
```
### 🥞 Set up your stack

```bash
zenml secrets-manager register AWS_SECRETS_MANAGER_NAME -t aws

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

Our docs regarding the evidently integration can be found [here](TODO: Link to docs).

If you want to learn more about visualizers in general or about how to build your own visualizers in zenml
check out our [docs](TODO: Link to docs)