# AWS Cloud Guide

This step-by-step guide explains how to set up and configure all the infrastructure necessary to run a ZenML pipeline on AWS.

## Prerequisites

- [Docker](https://www.docker.com/) installed and running.
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed.
- The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and authenticated.
- ZenML and the integrations for this tutorial stack installed:
    ```shell
    pip install zenml
    zenml integration install aws s3 kubernetes
    ```

## Setting up the AWS infrastructure

### Artifact Store (S3 bucket)
- Go to the [S3 website](https://s3.console.aws.amazon.com/s3/buckets).
- Click on `Create bucket`.
- Give it a descriptive name and note it down. You’ll need this name later to fill the `<S3_BUCKET_NAME>` placeholder.
- Select a region in which the bucket will be created.

### Metadata Store (RDS MySQL database)
- Go to the [RDS website](https://console.aws.amazon.com/rds).
- Make sure the correct region is selected on the top right (this region must be the same for all following steps).
- Click on `Create database`.
- Select `Easy Create`, `MySQL`, `Free tier` and enter values for your database name, username and password. Note down the username and password, we'll use them later for the `<RDS_MYSQL_USERNAME>` and `<RDS_MYSQL_PASSWORD>` placeholders.
- Wait until the deployment is finished.
- Select your new database and note down its endpoint. We'll use it later for the `<RDS_MYSQL_ENDPOINT>` placeholder.
- Click on the active VPC security group, select `Inbound rules` and click on `Edit inbound rules`
- Add a new rule with type `MYSQL/Aurora` and source `Anywhere-IPv4`.
- Go back to your database page and click on `Modify` in the top right.
- In the `Connectivity` section, open the `Advanced configuration` and enable public access.

### Container Registry (ECR)
- Go to the [ECR website](https://console.aws.amazon.com/ecr).
- Make sure the correct region is selected on the top right.
- Click on `Create repository`.
- Create a private repository called `zenml-kubernetes` with default settings.
- Note down the URI of your repository, we'll use it later for the `<ECR_URI>` placeholder.

### Orchestrator (EKS)
- Follow [this guide](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html#create-service-role) to create an Amazon EKS cluster role.
- Go to the [IAM website](https://console.aws.amazon.com/iam), select `Roles` and edit the role you just created.
- Click on `Add permissions` and select `Attach policies`.
- Attach the `SecretsManagerReadWrite`, `AmazonEKSClusterPolicy` and `AmazonS3FullAccess` policies to the role.
- Go to the [EKS website](https://console.aws.amazon.com/eks).
- Make sure the correct region is selected on the top right.
- Click on `Add cluster` and select `Create`.
- Enter a name and select our just created role for `Cluster service role`.
- Keep the default values for the networking and logging steps and create the cluster.
- After the cluster is created, select it and click on `Add node group` in the `Compute` tab.
- Enter a name and select the `EKSNodeRole`.
- Keep all other default values and create the node group.

## Register the ZenML stack

- Register the artifact store:
    ```shell
    zenml artifact-store register s3_store \
        --flavor=s3 \
        --path=s3://<S3_BUCKET_NAME>
    ```

- Register the container registry and authenticate your local docker client
    ```shell    
    zenml container-registry register ecr_registry \
        --flavor=aws \
        --uri=<ECR_URI>

    aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ECR_URI>
    ```

- Register the metadata store:
    ```shell
    zenml metadata-store register rds_mysql \
        --flavor=mysql \
        --database=zenml \
        --secret=rds_authentication \
        --host=<RDS_MYSQL_ENDPOINT>
    ```

- Register the secrets manager:
    ```shell
    zenml secrets-manager register aws_secrets_manager \
        --flavor=aws \
        --region_name=<REGION>
    ```

- Configure your `kubectl` client and register the orchestrator:
    ```shell
    aws eks --region <REGION> update-kubeconfig --name=<EKS_CLUSTER_NAME>
    kubectl create namespace zenml

    zenml orchestrator register eks_kubernetes_orchestrator \
        --flavor=kubernetes \
        --kubernetes_context=$(kubectl config current-context)
    ```

- Register the ZenML stack and activate it:
    ```shell
    zenml stack register kubernetes_stack \
        -o eks_kubernetes_orchestrator \
        -a s3_store \
        -m rds_mysql \
        -c ecr_registry \
        -x aws_secrets_manager \
        --set
    ```

- Register the secret for authenticating with your MySQL database:
    ```shell
    zenml secret register rds_authentication \
        --schema=mysql \
        --user=<RDS_MYSQL_USERNAME> \
        --password=<RDS_MYSQL_PASSWORD>
    ```

After all of this setup, you're now ready to run any ZenML pipeline on AWS!