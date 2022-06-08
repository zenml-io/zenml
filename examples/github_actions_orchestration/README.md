# 🏃 Run pipelines in GitHub Actions

# 🖥 Run it locally

## 👣 Step-by-Step
### 📄 Prerequisites 

In order to run this example, you need to install and initialize ZenML.

```bash
# install CLI
pip install zenml

# install ZenML integrations
zenml integration install github

# pull example
zenml example pull github_actions_orchestration

# Initialize ZenML repo
zenml init
```

### 🥞 Create a new GitHub Actions Stack

```bash
zenml orchestrator register github_orchestrator --flavor=github
zenml secrets_manager register github_secrets_manager --flavor=github --owner=<GITHUB_REPOSITORY_OWNER> --repository=<GITHUB_REPOSITORY_NAME>
zenml stack register github_stack \
    -m default \
    -a default \
    -o github_orchestrator \
    -s github_secrets_manager \
    -c container_registry
    --set
```

### 📆 Run or schedule the pipeline

```bash
python run.py
```

# 📜 Learn more

If you want to learn more about orchestrators in general or about how to build your own orchestrators in ZenML
check out our [docs](https://docs.zenml.io/extending-zenml/orchestrator).
