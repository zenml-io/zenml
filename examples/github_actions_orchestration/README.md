# 🏃 Run pipelines in GitHub Actions

# 🖥 Run it locally

## 👣 Step-by-Step
### 📄 Prerequisites 

In order to run this example, you need to install and initialize ZenML.

```bash
pip install zenml

# Install ZenML integrations: choose one of s3/gcp/azure depending on where your artifact store is hosted
zenml integration install github <s3/gcp/azure>

cd <ROOT_OF_YOUR_GITHUB_REPOSITORY>


# If your git repository does not contain an existing ZenML pipeline, we can use the sample pipeline from this example
zenml example pull github_actions_orchestration
cp zenml_examples/github_actions_orchestration/run.py .
rm -rf zenml_examples
git add run.py
git commit -m "Add ZenML example pipeline"
```

### 🥞 Create a new GitHub Actions Stack

```bash
export GITHUB_USERNAME=<>
export GITHUB_AUTHENTICATION_TOKEN=<>

zenml orchestrator register github_orchestrator --flavor=github
zenml container-registry register github_container_registry --flavor=github --uri=<CR_URI> --automatic_token_authentication=true

zenml secrets_manager register github_secrets_manager --flavor=github --owner=<GITHUB_REPOSITORY_OWNER> --repository=<GITHUB_REPOSITORY_NAME>

# Register a metadata store and a secret to connect to it
zenml secret register mysql_secret --schema=mysql --user=<USERNAME> --password=<PASSWORD> --ssl_ca=<> --ssl_cert=<> --ssl_key=<>
zenml metadata-store register cloud_metadata_store --flavor=mysql --host=<HOST> --database=<DATABASE_NAME> --secret=mysql_secret

# Register one of the three following artifact stores and a secret to connect to it
# 1) AWS
zenml secret register s3_store_auth --schema=aws --aws_access_key_id=<ACCESS_KEY_ID> --aws_secret_access_key=<SECRET_ACCESS_KEY>
zenml artifact-store register cloud_artifact_store --flavor=s3 --path=<YOUR_S3_BUCKET_PATH> --authentication_secret=s3_store_auth

# 2) GCP
zenml secret register gcp_store_auth --schema=gcp ...
zenml artifact-store register cloud_artifact_store --flavor=gcp --path=<YOUR_GCP_BUCKET_PATH> --authentication_secret=gcp_store_auth

# 3) AZURE
zenml secret register azure_store_auth --schema=azure ...
zenml artifact-store register cloud_artifact_store --flavor=azure --path=<YOUR_AZURE_BUCKET_PATH> --authentication_secret=azure_store_auth


zenml stack register github_stack \
    -o github_orchestrator \
    -s github_secrets_manager \
    -c github_container_registry \
    -m cloud_metadata_store \
    -a cloud_artifact_store \
    --set
```

### 📆 Run or schedule the pipeline

```bash
python run.py
```

# 📜 Learn more

If you want to learn more about orchestrators in general or about how to build your own orchestrators in ZenML
check out our [docs](https://docs.zenml.io/extending-zenml/orchestrator).
