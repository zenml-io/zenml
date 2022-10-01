---
description: Deploying ZenML on cloud using the CLI
---

The easiest and fastest way to get running on the cloud is by using the `deploy` CLI command. It currently only supports deploying to Kubernetes on managed cloud services. You can check the [overview page](./deployment.md) to learn other options that you have.  

Before we begin, it will help to understand the [architecture](./how-it-works.md) around the ZenML server and the database that it uses. Now, depending on your setup, you may find one of the following scenarios relevant.

## Scenario 1: Starting from scratch

If you don't have an existing Kubernetes cluster, you have the following two options to set it up:
- Creating it manually using the documentation for your cloud provider. For convenience, here are links for [AWS](https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html), [Azure](https://learn.microsoft.com/en-us/azure/aks/learn/quick-kubernetes-deploy-portal?tabs=azure-cli) and [GCP](https://cloud.google.com/kubernetes-engine/docs/how-to/creating-a-zonal-cluster#before_you_begin).
- Using [stack recipes](../practical/stack-recipes.md) that set up a cluster along with other tools that you might need in your cloud stack like artifact stores, and secret managers. Take a look at all [available stack recipes](https://github.com/zenml-io/mlops-stacks#-list-of-recipes) to see if there's something that works for you.

> **Note**
> Once you have created your cluster, make sure that you configure your [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) client to talk to it. If you have used stack recipes, this step is already done for you!

You're now ready to deploy ZenML! Run the following command:
```
zenml deploy
```
You will be prompted to provide a name for your deployment and details like what cloud provider you want to deploy to, in addition to the username, password and email you want to set for the default user — and that's it! It creates the database and any VPCs, permissions and more that is needed.

> **Note**
> To be able to run the deploy command, you should have your cloud provider's CLI configured locally with permissions to create resoureces like MySQL databases and networks.

Reasonable defaults are in place for you already and if you wish to configure more settings, take a look at the next scenario that uses a config file.

## Scenario 2: Using existing cloud resources

If you already have an existing cluster with your local `kubectl` configured with it, you can jump straight to the `deploy` command above to get going with the defaults. 

However, if you also already have a database that you would want to use with the deployment you can choose to configure it with the use of a config file. This file can be found in the Resources section towards the end of this guide. It offers a host of configuration options that you can leverage for advanced use cases. Here we will demonstrate setting the database.

- Fill the fields below from the config file with values from your database.

    ```
    rds_db_username: The username for the RDS database.
    rds_db_password: The password for the RDS database.
    
    database_url: The URL of the database to use for the ZenML server.
    database_ssl_ca: The path to the SSL CA certificate to use for the
        database connection.
    database_ssl_cert: The path to the client SSL certificate to use for the
        database connection.
    database_ssl_key: The path to the client SSL key to use for the
        database connection.
    database_ssl_verify_server_cert: Whether to verify the database server
        SSL certificate.
    ```

- Run the `deploy` command and pass the config file above to it.

    ```
    zenml deploy --config=/PATH/TO/FILE
    ```
    > **Note**
    > To be able to run the deploy command, you should have your cloud provider's CLI configured locally with permissions to create resoureces like MySQL databases and networks.


> **Note**
> Only MySQL version 5.7.x are supported by ZenML, currently.

## Configuration File Templates

