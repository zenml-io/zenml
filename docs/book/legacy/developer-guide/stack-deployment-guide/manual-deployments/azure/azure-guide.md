---
description: How to set up a minimal stack on Microsoft Azure
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Getting started with Azure

To get started using ZenML on the cloud, you need some basic infrastructure up 
and running which ZenML can use to run your pipelines.
This step-by-step guide explains how to set up a basic cloud stack on Azure.

{% hint style="info" %}
This guide represents **one** of many ways to create a cloud stack on Azure. 
You can customize this by adding additional components of replacing one of the 
components described in this guide.
{% endhint %}

## What will the stack look like?



## Prerequisites

- [Docker](https://www.docker.com/) installed and running.
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed.
- The [az CLI](https://docs.microsoft.com/en-us/cli/azure/) installed and authenticated.
- ZenML and the integrations for this tutorial stack installed:
    ```shell
    pip install zenml
    zenml integration install azure kubernetes
    ```

## Setting up the Azure resources

All the Azure setup steps can either be done using the Azure UI or CLI. Simply select the tab for your preferred option and let's get started.
First open up a terminal which we'll use to store some values along the way which we'll need to configure our ZenML stack later.

### Create an account

If you don't have an Azure account yet, go to [https://azure.microsoft.com/en-gb/free/](https://azure.microsoft.com/en-gb/free/) and create one.

### Create a resource group

[Resource groups](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/overview#resource-groups) are a concept in Azure that allows us to bundle different resources that share a similar lifecycle. We'll create a new resource group for this tutorial so we'll be able to differentiate them from other resources in our account and easily delete them at the end.

> When creating a resource group, you need to provide a location for that resource group. You may be wondering, "Why does a resource group need a location? And, if the resources can have different locations than the resource group, why does the resource group location matter at all?" The resource group stores metadata about the resources. Therefore, when you specify a location for the resource group, you are specifying where that metadata is stored. For compliance reasons, you may need to ensure that your data is stored in a particular region.
>https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-overview

{% tabs %}
{% tab title="Azure UI" %}

- Go to [the Azure portal](https://portal.azure.com/#home), click the hamburger button in the top left to open up the portal menu. Then, hover over the `Resource groups` section until a popup appears and click on the `+ Create` button.

- Select a region and enter a name for your resource group before clicking on `Review + create`.

- Verify that all the information is correct and click on `Create`.
- Set the following variables in your shell.

    ```shell
    RESOURCE_GROUP=<RESOURCE_GROUP_NAME>
    RG_LOCATION=<RG_LOCATION>
    ```

{% endtab %}

{% tab title="Azure CLI" %}

```shell
RESOURCE_GROUP=<RESOURCE_GROUP_NAME>
RG_LOCATION=<RG_LOCATION>
az group create --name $RESOURCE_GROUP --location $RG_LOCATION
```

{% endtab %}
{% endtabs %}


### Create a storage account

An [Azure storage account](https://docs.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal) is a grouping of Azure data storage objects which also provides a namespace and authentication options to access them. We'll need a storage account to hold the blob storage container we'll create in the next step.

{% tabs %}
{% tab title="Azure UI" %}

- Open up the portal menu again, but this time hover over the `Storage accounts` section and click on the `+ Create` button in the popup once it appears: 


- Select your previously created **resource group**, a **region** and a **globally unique name** and then click on `Review + create`:

- Make sure that all the values are correct and click on `Create`:

- Wait until the deployment is finished and click on `Go to resource` to open up your newly created storage account:

- In the left menu, select `Access keys`:

- Click on `Show keys`, and once the keys are visible, note down the **storage account name** and the value of the **Key** field of either key1 or key2.
    We're going to use them for the `<STORAGE_ACCOUNT_NAME>` and `<STORAGE_ACCOUNT_KEY>` placeholders later.

- Set the following variables in your shell.

    ```shell
    REGION=<REGION>
    STORAGE_ACCOUNT_NAME=<STORAGE_ACCOUNT_NAME>
    STORAGE_ACCOUNT_KEY=<STORAGE_ACCOUNT_KEY>
    ```

{% endtab %}

{% tab title="Azure CLI" %}

```shell
# Set a name for your bucket and the Azure region for your resources
REGION=<REGION>  
STORAGE_ACCOUNT_NAME=<STORAGE_ACCOUNT_NAME>

az storage account create -n $STORAGE_ACCOUNT_NAME -g $RESOURCE_GROUP -l $REGION
STORAGE_ACCOUNT_KEY=$(az storage account keys list -g $RESOURCE_GROUP -n $STORAGE_ACCOUNT_NAME --query [0].value -o tsv)

```

{% endtab %}
{% endtabs %}


### Create an Azure Blob Storage Container

Next, we're going to create an [Azure Blob Storage Container](https://docs.microsoft.com/en-us/azure/storage/blobs/). It will be used by ZenML to store the output artifacts of all our pipeline steps.

{% tabs %}
{% tab title="Azure UI" %}

- To do so, select `Containers` in the Data storage section of the storage account:


- Then click the `+ Container` button on the top to create a new container:

- Choose a name for the container and note it down. We're going to use it later for the `<BLOB_STORAGE_CONTAINER_NAME>` placeholder. Then create the container by clicking the `Create` button.

- Set the following variables in your shell.

    ```shell
    BLOB_STORAGE_CONTAINER_NAME=<BLOB_STORAGE_CONTAINER_NAME>
    ```


{% endtab %}

{% tab title="Azure CLI" %}

```shell
BLOB_STORAGE_CONTAINER_NAME=<BLOB_STORAGE_CONTAINER_NAME> 
az storage container create --$BLOB_STORAGE_CONTAINER_NAME
```

{% endtab %}
{% endtabs %}

### Set up a MySQL database

Now let's set up a managed MySQL database. This will act as ZenML's metadata store and store metadata regarding our pipeline runs which will enable features like caching and establish a consistent lineage between our pipeline steps.

{% tabs %}
{% tab title="Azure UI" %}

- Open up the portal menu and click on `+ Create a resource`.

- Search for `Azure Database for MySQL` and once found click on `Create`.Make sure you select `Flexible server` and then continue by clicking the `Create` button.

- Select a **resource group** and **region** and fill in values for the **server name** as well as **admin username** and **password**. Note down the username and password you chose as we're going to need them later for the `<MYSQL_USERNAME>` and `<MYSQL_PASSWORD>` placeholders. Then click on `Next: Networking`.

- Now click on `Add 0.0.0.0 - 255.255.255.255` to allow access from all public IPs. This is necessary so the machines running our GitHub Actions can access this database. It will still require username, password as well as a SSL certificate to authenticate.

- In the opened up popup, click on `Continue` and click on `Review + create`.

- Verify the configuration and click the `Create` button. Now we'll have to wait until the deployment is finished (this might take ~15 minutes).

**Note**: If the deployment fails for some reason, delete the resource and restart from the beginning of [this section](#set-up-a-mysql-database).

- Once the deployment is finished, click on `Go to resource`.

- On the overview page of your MySQL server resource, note down the server name in the top right. We'll use it later for the `<MYSQL_SERVER_NAME>` placeholder.

- Then click on `Networking` in the left menu. Click on `Download SSL Certificate` on the top. Make sure to note down the path to the certificate file which we'll use for the `<PATH_TO_SSL_CERTIFICATE>` placeholder in a later step.

- Set the following values in your shell.
    ```shell
    MYSQL_SERVER_NAME=<MYSQL_SERVER_NAME>
    PATH_TO_SSL_CERTIFICATE=<PATH_TO_SSL_CERTIFICATE>
    MYSQL_USERNAME=<MYSQL_USERNAME>
    MYSQL_PASSWORD=<MYSQL_PASSWORD>
    ```

{% endtab %}

{% tab title="Azure CLI" %}

```shell

MYSQL_SERVER_INSTANCE_NAME=<MYSQL_SERVER_INSTANCE_NAME>
MYSQL_USERNAME=<MYSQL_USERNAME>
MYSQL_PASSWORD=<MYSQL_PASSWORD>

az mysql flexible-server create -l $REGION -g $RESOURCE_GROUP \
 -n $MYSQL_SERVER_INSTANCE_NAME -u $MYSQL_USERNAME -p $MYSQL_PASSWORD \
 --public-access 0.0.0.0-255.255.255.255

MYSQL_SERVER_NAME="$MYSQL_SERVER_INSTANCE_NAME.mysql.database.azure.com"

PATH_TO_SSL_CERTIFICATE=<PATH_TO_SSL_CERTIFICATE>  # should end with a filename like, /../../certificate.pem
wget --no-check-certificate https://dl.cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem -O $PATH_TO_SSL_CERTIFICATE
```

{% endtab %}
{% endtabs %}

### Container Registry

{% tabs %}
{% tab title="Azure UI" %}

* [Set up](https://azure.microsoft.com/en-in/services/container-registry/#get-started)
  an Azure Container Registry (ACR).

* Set the regsitry name in your shell.

  ```shell
  REGISTRY_NAME=<REGISTRY_NAME>  # should be <some-name>.azurecr.io
  ```
 

{% endtab %}

{% tab title="Azure CLI" %}

```shell
REGISTRY_NAME=<REGISTRY_NAME>  # should be <some-name>.azurecr.io

az acr create -n $REGISTRY_NAME -g $RESOURCE_GROUP
```

{% endtab %}
{% endtabs %}

### Orchestrator (Azure Kubernetes Service)

{% tabs %}
{% tab title="Azure UI" %}

- On the Azure portal menu or from the Home page, select Create a resource. Select `Containers` > `Kubernetes Service`.

- On the Basics page, configure the following options. Under Project details,
    - Select your Azure Subscription.
    - Select your Resource group.
    
- Under Cluster details,
    - Ensure the the Preset configuration is Standard ($$). For more details on preset configurations, see Cluster configuration presets in the Azure portal.
    - Enter a Kubernetes cluster name. We will use it later as <AKS_CLUSTER_NAME>
- Enter your `Region` for the AKS cluster, and leave the default value selected for Kubernetes version.
- Keep the default values for all other sections and click on `Review + Create`.
- Set the following variable in your shell.
    ```shell
    AKS_CLUSTER_NAME=<AKS_CLUSTER_NAME> 
    ```


{% endtab %}

{% tab title="Azure CLI" %}

```shell
AKS_CLUSTER_NAME=<AKS_CLUSTER_NAME> 

az aks create -g $RESOURCE_GROUP -n $AKS_CLUSTER_NAME --node-count 1 \
 --enable-cluster-autoscaler 
```

{% endtab %}
{% endtabs %}

## Register the ZenML stack

- Register the artifact store:
    ```shell
    zenml artifact-store register azure_store \
        --flavor=azure \
        --path=az://$BLOB_STORAGE_CONTAINER_NAME
    ```

- Register the container registry and authenticate your local docker client
    ```shell    
    zenml container-registry register acr_registry \
        --flavor=azure \
        --uri=$REGISTRY_NAME
    az acr login --name $REGISTRY_NAME
    ```

- Register the metadata store:
    ```shell
    zenml metadata-store register azure_mysql \
        --flavor=mysql \
        --database=zenml \
        --secret=azure_authentication \
        --host=$MYSQL_SERVER_NAME
    ```

- Register the secrets manager:
    ```shell
    zenml secrets-manager register azure_secrets_manager \
        --flavor=azure \
        --region_name=$REGION
    ```

- Configure your `kubectl` client and register the orchestrator:
    ```shell
    az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME
    kubectl create namespace zenml
    zenml orchestrator register aks_kubernetes_orchestrator \
        --flavor=kubernetes \
        --kubernetes_context=$(kubectl config current-context)
    ```

- Register the ZenML stack and activate it:
    ```shell
    zenml stack register kubernetes_stack \
        -o aks_kubernetes_orchestrator \
        -a azure_store \
        -m azure_mysql \
        -c acr_registry \
        -x azure_secrets_manager \
        --set
    ```

- Register the secret for authenticating with your MySQL database:
    ```shell
    zenml secrets-manager secret register azure_authentication \
        --schema=mysql \
        --user=$MYSQL_USERNAME \
        --password=$MYSQL_PASSWORD
    ```


After all of this setup, you're now ready to run any ZenML pipeline on Azure!

## Quick setup

If you're looking for a way to get started quickly, we've combined all the commands so you can copy-paste them and execute them in a single go. You'll only need to set values for the `<REGION>`, `<RESOURCE_GROUP>` and `<MYSQL_PASSWORD>` right at the beginning before executing the rest. If you're on Windows, also adjust the certificate path accordingly.

<details>
    <summary>Quick setup commands</summary>


```shell

# Select one of the region codes for <REGION>: https://docs.microsoft.com/en-us/azure/availability-zones/az-overview#azure-regions-with-availability-zones
REGION=<REGION>  
RESOURCE_GROUP=<RESOURCE_GROUP>
# Choose a secure password for your database admin account. Make sure it includes:
# - at least 8 printable ASCII characters
# - no slash, single or double quotes or @ signs
MYSQL_PASSWORD=<MYSQL_PASSWORD>

# Other parameters (we've set some defaults for these but feel free to change them):
RG_LOCATION=westus
STORAGE_ACCOUNT_NAME=zenml-storage-account
BLOB_STORAGE_CONTAINER_NAME=zenml-artifact-store
MYSQL_SERVER_INSTANCE_NAME=zenml-metadata-store
MYSQL_USERNAME=admin
REGISTRY_NAME=zenml
PATH_TO_SSL_CERTIFICATE="./certificate.pem"  # WINDOWS USERS, use the backslash
AKS_CLUSTER_NAME=zenml-aks-cluster

az group create --name $RESOURCE_GROUP --location $RG_LOCATION

# storage account
az storage account create -n $STORAGE_ACCOUNT_NAME -g $RESOURCE_GROUP -l $REGION
STORAGE_ACCOUNT_KEY=$(az storage account keys list -g $RESOURCE_GROUP -n $STORAGE_ACCOUNT_NAME --query [0].value -o tsv)

az storage container create --$BLOB_STORAGE_CONTAINER_NAME

# MySQL database
az mysql flexible-server create -l $REGION -g $RESOURCE_GROUP \
 -n $MYSQL_SERVER_INSTANCE_NAME -u $MYSQL_USERNAME -p $MYSQL_PASSWORD \
 --public-access 0.0.0.0-255.255.255.255

MYSQL_SERVER_NAME="$MYSQL_SERVER_INSTANCE_NAME.mysql.database.azure.com"

wget --no-check-certificate https://dl.cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem -O $PATH_TO_SSL_CERTIFICATE

# container registry
az acr create -n $REGISTRY_NAME -g $RESOURCE_GROUP

# orchestrator
az aks create -g $RESOURCE_GROUP -n $AKS_CLUSTER_NAME --node-count 1 \
 --enable-cluster-autoscaler 

# register with zenml

zenml artifact-store register azure_store \
    --flavor=azure \
    --path=az://$BLOB_STORAGE_CONTAINER_NAME

zenml container-registry register acr_registry \
    --flavor=azure \
    --uri=$REGISTRY_NAME
az acr login --name $REGISTRY_NAME

zenml metadata-store register azure_mysql \
    --flavor=mysql \
    --database=zenml \
    --secret=azure_authentication \
    --host=$MYSQL_SERVER_NAME

zenml secrets-manager register azure_secrets_manager \
    --flavor=azure \
    --region_name=$REGION

az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME
kubectl create namespace zenml
zenml orchestrator register aks_kubernetes_orchestrator \
    --flavor=kubernetes \
    --kubernetes_context=$(kubectl config current-context)

zenml stack register kubernetes_stack \
    -o aks_kubernetes_orchestrator \
    -a azure_store \
    -m azure_mysql \
    -c acr_registry \
    -x azure_secrets_manager \
    --set

zenml secrets-manager secret register azure_authentication \
    --schema=mysql \
    --user=$MYSQL_USERNAME \
    --password=$MYSQL_PASSWORD

```
</details>
