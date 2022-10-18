# 🥙 Azure Minimal MLOps Stack Recipe 

There can be many motivations behind taking your ML application setup to a cloud environment, from neeeding specialized compute 💪 for training jobs to having a 24x7 load-balanced deployment of your trained model serving user requests 🚀.

We know that the process to set up an MLOps stack can be daunting. There are many components (ever increasing) and each have their own requirements. To make your life easier, we already have a [documentation page](https://docs.zenml.io/cloud-guide/overview) that takes you step-by-step through the entire journey in a cloud platform of your choice (AWS, GCP and Azure supported for now). This recipe, however, goes one step further. 

You can have a simple MLOps stack ready for running your machine learning workloads after you execute this recipe 😍. It sets up the following resources: 
- An AKS cluster that can act as an [orchestrator](https://docs.zenml.io/mlops-stacks/orchestrators) for your workloads.
- An Azure Blob Storage Container as an [artifact store](https://docs.zenml.io/mlops-stacks/artifact-stores), which can be used to store all your ML artifacts like the model, checkpoints, etc. 
- A MySQL Flexible server instance as a [metadata store](https://docs.zenml.io/mlops-stacks/metadata-stores) that is essential to track all your metadata and its location in your artifact store.  
- An Azure Container Registry instance for storing your docker images. 
- An MLflow tracking server as an [experiment tracker](https://docs.zenml.io/mlops-stacks/experiment-trackers) which can be used for logging data while running your applications. It also has a beautiful UI that you can use to view everything in one place.
- A Seldon Core deployment as a [model deployer](https://docs.zenml.io/mlops-stacks/model-deployers) to have your trained model deployed on a Kubernetes cluster to run inference on. 

Keep in mind, this is a basic setup to get you up and running on GCP with a minimal MLOps stack and more configuration options are coming in the form of new recipes! 👀

## Prerequisites

* You must have a GCP project where you have sufficient permissions to create and destroy resources that will be created as part of this recipe. Supply the name of your project in the `locals.tf` file.
* Have [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli#install-terraform) and [Helm](https://helm.sh/docs/intro/install/#from-script) installed on your system.


## 🍏 Inputs

Before starting, you should know the values that you have to keep ready for use in the script. 
- Check out the `locals.tf` file to configure basic information about your deployments.
- Take a look at the `values.tfvars.json` file to know what values have to be supplied during the execution of the script. These are mostly sensitive values like MLflow passwords, AWS access keys, etc. Make sure you don't commit them!

> **Warning** 
> The `prefix` local variable you assign should have a unique value for each stack. This ensures that the stack you create doesn't interfere with the stacks somebody else in your organization has created with this script.

> **Warning**
> The CIDR block used for the VPC (inside the vpc.tf file) needs to be unique too, preferably. For example, if `10.10.0.0/16` is already under use by some VPC in your account, you can use `10.11.0.0/16` instead. However, this is not required.

## 🧑‍🍳 Cooking the recipe

It is not neccessary to use the MLOps stacks recipes presented here alongisde the
[ZenML](https://github.com/zenml-io/zenml) framework. You can simply use the Terraform scripts
directly.

However, ZenML works seamlessly with the infrastructure provisioned through these recipes. The ZenML CLI has an integration with this repository that makes it really simple to pull and deploy these recipes. A simple flow could look like the following:

1. Pull this recipe to your local system.

    ```shell
    zenml stack recipe pull azure-minimal
    ```
2. 🎨 Customize your deployment by editing the default values in the `locals.tf` file.

3. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

5. 🚀 Deploy the recipe with this simple command.

    ```
    zenml stack recipe deploy azure-minimal
    ```

    > **Note**
    > If you want to allow ZenML to automatically import the created resources as a ZenML stack, pass the `--import` flag to the command above. By default, the imported stack will have the same name as the stack recipe and you can provide your own with the `--stack-name` option.
    

6. You'll notice that a ZenML stack configuration file gets created after the previous command executes 🤯! This YAML file can be imported as a ZenML stack manually by running the following command.

    ```
    zenml stack import <STACK-NAME> <PATH-TO-THE-CREATED-STACK-CONFIG-YAML>

    # set the stack as an active stack
    zenml stack set <STACK-NAME>
    ```

> **Note**
>
>  You need to have your local `az` client logged in. Run `az login` if not done already.

### Configuring your secrets

To make the imported ZenML stack work, you'll have to create secrets that some stack components need. If you inspect the generated YAML file, you can figure out that three secrets should be created:

- `azure-storage-secret` - for allowing access to the Azure Blob Storage Container.

    - Go into your imported recipe directory. It should be under `zenml_stack_recipes/azure-minimal`.
    - Run the following commands to get the storage account name and key.
        ```
        terraform output storage-account-name

        terraform output storage-account-key
        ```
    - Now, register your ZenML secret.
        ```
        zenml secrets-manager secret register azure-storage-secret --schema=azure --account_name=<ACCOUNT_NAME> --account_key=<ACCOUNT_KEY>
        ```

- `azure_seldon_secret` - for allowing Seldon access to the Azure Blob Storage container.

    - We will re-use the storage account name and the storage account key from the storage secret.
    - Now, register the ZenML secret.
        ```
        zenml secrets-manager secret register -s seldon_azure azure-seldon-secret --rclone_config_azureblob_account=<ACCOUNT_NAME> --rclone_config_azureblob_key=<ACCOUNT_KEY>
        ```

- `azure-mysql-secret` - for allowing access to the Flexible MySQL instance.

    - Go into your imported recipe directory. It should be under `zenml_stack_recipes/azure-minimal`.
    - Run the following commands to get the username and password for the MySQL instance.
        ```
        terraform output metadata-db-username

        terraform output metadata-db-password
        ```
    
    - An SSL certificate is already downloaded as part of recipe execution and will be available in the recipe directory with name `DigiCertGlobalRootCA.crt.pem`
    - Now, register the ZenML secret using the following command.
        ```
        zenml secrets-manager secret register azure-mysql-secret --schema=mysql --user=<USERNAME> --password=<PASSWORD> --ssl_ca=@"<PATH-TO-THE-CERTIFICATE"
        ```


If you face a `ClientAuthorizationError` while trying to create secrets, add the relevant permissions to your account using the following command. 

- Get the key vault name by running the command:
    ```
    terraform output key-vault-name
    ```

- Find your Azure object ID. You can also get it from the error message you see.
    ```
    az ad user show --id <YOUR_AZURE_EMAIL>
    ```
- Set permissions for your object ID.
    ```
    az keyvault set-policy --name <KEY_VAULT_NAME> --object-id <YOUR_OBJECT_ID> --secret-permissions get list set delete --key-permissions create delete get list`
    ```


## 🥧 Outputs 

The script, after running, outputs the following.
| Output | Description |
--- | ---
aks-cluster-name | Name of the AKS cluster that is created. This is helpful when setting up `kubectl` access |
blobstorage-container-path | The Azure Blob Storage Container path for storing your artifacts|
storage-account-name | The name of the Azure Blob Storage account name|
storage-account-key | The Azure Blob Storage account key |
mlflow-tracking-URI | The URL for the MLflow tracking server |
seldon-core-workload-namespace | Namespace in which seldon workloads will be created |
seldon-base-url | The URL to use for your Seldon deployment |
metadata-db-host | The host endpoint of the deployed metadata store |
metadata-db-username | The username for the database user |
metadata-db-password | The master password for the database |
container-registry-URL | Container registry URL |
key-vault-name | The name of the Azure Key Vault created |


For outputs that are sensitive, you'll see that they are not shown directly on the logs. To view the full list of outputs, run the following command.

```bash
terraform output
```

To view individual sensitive outputs, use the following format. Here, the metadata password is being obtained. 

```bash
terraform output metadata-db-password
```

## Deleting Resources

Using the ZenML stack recipe CLI commands, you can run the following commands to delete your resources and optionally clean up the recipe files that you had downloaded to your local system.

1. 🗑️ Run the destroy command which removes all resources and their dependencies from the cloud.

    ```shell
    zenml stack recipe destroy azure-minimal
    ```

2. (Optional) 🧹 Clean up all stack recipe files that you had pulled to your local system.

    ```shell
    zenml stack recipe clean
    ```


## Using the recipes without the ZenML CLI

As mentioned above, you can still use the recipe without having using the `zenml stack recipe` CLI commands or even without installing ZenML. Since each recipe is a group of Terraform modules, you can simply employ the terraform CLI to perform `apply` and `destroy` operations.

### Create the resources

1. 🎨 Customize your deployment by editing the default values in the `locals.tf` file.

2. 🔐 Add your secret information like keys and passwords into the `values.tfvars.json` file which is not committed and only exists locally.

3. Initiliaze Terraform modules and download provider definitions.
    ```bash
    terraform init
    ```

4. Apply the recipe.
    ```bash
    terraform apply
    ```

### Deleting resources

1. 🗑️ Run the destroy function to clean up all resources.

    ```
    terraform destroy
    ```

