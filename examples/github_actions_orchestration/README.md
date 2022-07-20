# 🏃 Run pipelines using GitHub Actions

[GitHub Actions](https://docs.github.com/en/actions) is a platform that allows you to execute
arbitrary software development workflows right in your GitHub repository. It's most commonly used for CI/CD pipelines, but using the **GitHub Actions orchestrator** ZenML now enables you to easily run and schedule 
your machine learning pipelines as GitHub Actions workflows.

## 📄 Prerequisites

In order to run your ZenML pipelines using GitHub Actions, we need to set up a few things first:

* First you'll need a [GitHub](https://github.com) account and a cloned repository.
* You'll also need to create a GitHub personal access token that allows you read/write GitHub secrets and push Docker images to your GitHub container registry. To do so, please follow [this guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) and make sure to assign your token the **repo** and **write:packages** scopes.
* A MySQL database that ZenML will use to store metadata. See [here](https://docs.zenml.io/cloud-guide/overview) for more information on how to set one up on AWS/GCP/Azure.
* An artifact store to save the outputs of your pipeline steps. See [here](https://docs.zenml.io/cloud-guide/overview) for more information on how to set one up on AWS/GCP/Azure.

```bash
pip install zenml

# Install ZenML integrations: choose one of s3/gcp/azure depending on where your artifact store is hosted
zenml integration install github <s3/gcp/azure>

# Change the current working directory to a path inside your cloned GitHub repository
cd <PATH_INSIDE_GITHUB_REPOSITORY>

# If your git repository already contains a ZenML pipeline, you can skip these next few commands
zenml example pull github_actions_orchestration --path=.
git add github_actions_orchestration
git commit -m "Add ZenML example pipeline"
cd github_actions_orchestration

# Set environment variables for your GitHub username as well as the personal access token that you created earlier.
# These will be used to authenticate with the GitHub API in order to store credentials as GitHub secrets.
export GITHUB_USERNAME=<GITHUB_USERNAME>
export GITHUB_AUTHENTICATION_TOKEN=<GITHUB_AUTHENTICATION_TOKEN>

# Login to the GitHub container registry so we can push the Docker images required to run your ZenML pipeline.
echo $GITHUB_AUTHENTICATION_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin
```

## 🥞 Create a new GitHub Actions Stack

Once we have finished all the external setup, we can create a ZenML stack that 
connects all these elements together:

```bash
# We configure the orchestrator to automatically commit and push the GitHub workflow file. If you want to disable this behavior, simply remove the `--push=true` argument
zenml orchestrator register github_orchestrator --flavor=github --push=true  

# You can find the repository owner and repository name from the URL of your GitHub repository,
# for example https://github.com/zenml-io/zenml -> The owner would be `zenml-io` and the repository name `zenml`
zenml secrets-manager register github_secrets_manager \
    --flavor=github \
    --owner=<GITHUB_REPOSITORY_OWNER> \
    --repository=<GITHUB_REPOSITORY_NAME>

# The GITHUB_CONTAINER_REGISTRY_URI format will be like this: ghcr.io/GITHUB_REPOSITORY_OWNER
zenml container-registry register github_container_registry \
    --flavor=github \
    --automatic_token_authentication=true \
    --uri=<GITHUB_CONTAINER_REGISTRY_URI>

# Register a metadata store (we will create the authentication secret later)
# - HOST is the public IP address of your MySQL database
# - DATABASE_NAME is the name of the database in which ZenML should store metadata
zenml metadata-store register cloud_metadata_store \
    --flavor=mysql \
    --secret=mysql_secret \
    --host=<HOST> \
    --database=<DATABASE_NAME> \

# Register one of the three following artifact stores (we will create the authentication secrets later)
# AWS:
zenml artifact-store register cloud_artifact_store \
    --flavor=s3 \
    --authentication_secret=s3_store_auth \
    --path=<S3_BUCKET_PATH>
# GCP:
zenml artifact-store register cloud_artifact_store \
    --flavor=gcp \
    --authentication_secret=gcp_store_auth \
    --path=<GCP_BUCKET_PATH>
# AZURE:
zenml artifact-store register cloud_artifact_store \
    --flavor=azure \
    --authentication_secret=azure_store_auth \
    --path=<AZURE_BUCKET_PATH>

# Register and activate the stack
zenml stack register github_stack \
    -o github_orchestrator \
    -s github_secrets_manager \
    -c github_container_registry \
    -m cloud_metadata_store \
    -a cloud_artifact_store \
    --set

# Now that the stack is active, we can register the secrets needed to connect to our metadata and artifact store:
zenml secret register mysql_secret \
    --schema=mysql \
    --user=<USERNAME> \
    --password=<PASSWORD> \
    --ssl_ca=@<PATH_TO_SSL_SERVER_CERTIFICATE> \
    --ssl_cert=@<PATH_TO_SSL_CLIENT_CERTIFICATE> \
    --ssl_key=@<PATH_TO_SSL_CLIENT_KEY>

# Register one of the following secrets depending on the flavor of artifact store that you've registered:
# AWS: See https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html for how to
# create the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY to authenticate with your S3 bucket
zenml secret register s3_store_auth \
    --schema=aws \
    --aws_access_key_id=<AWS_ACCESS_KEY_ID> \
    --aws_secret_access_key=<AWS_SECRET_ACCESS_KEY>
# GCP: The PATH_TO_GCP_TOKEN can be either a token generated by the `gcloud` CLI utility 
# (e.g. ~/.config/gcloud/application_default_credentials.json) or a service account file
zenml secret register gcp_store_auth \
    --schema=gcp \
    --token=@<PATH_TO_GCP_TOKEN>
# AZURE: See https://docs.microsoft.com/en-us/azure/storage/common/storage-account-keys-manage?tabs=azure-portal
# for how to find your AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY
zenml secret register azure_store_auth \
    --schema=azure \
    --account_name=<AZURE_ACCOUNT_NAME> \
    --account_key=<AZURE_ACCOUNT_KEY>
```

## ▶️ Run the pipeline

We're almost done now, but there is one additional step we need to do after our first pipeline ran (and failed). To do so, simply call

```bash
python run.py
```

Running your first pipeline using the ZenML GitHub Actions orchestrator will create a [GitHub package](https://github.com/features/packages) called **zenml-github-actions** which by default won't be accessible by GitHub Actions.
Luckily it doesn't take much effort to resolve this problem: Head to `https://github.com/users/<GITHUB_REPOSITORY_OWNER>/packages/container/package/zenml-github-actions` (replace <GITHUB_REPOSITORY_OWNER> with the value you passed earlier during stack configuration) and click on `Package settings` on the right side. In there you can either
* change the package visibility to `public`
* give your repository permissions to access this package using GitHub Actions in the `Manage Actions access` section (see [here](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility#ensuring-workflow-access-to-your-package))

After this final step we can try again, and this time it should work:

```bash
python run.py
```

That's it! If everything went as planned, this pipeline should now be running in
GitHub Actions and you should be able to access it from the GitHub UI. It will look something like this:

![GitHub Actions UI](assets/github_actions_ui.png)

# 📜 Learn more

If you want to learn more about orchestrators in general or about how to build your own orchestrators in ZenML
check out our [docs](https://docs.zenml.io/mlops-stacks/orchestrators).
