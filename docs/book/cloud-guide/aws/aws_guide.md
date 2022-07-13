# Getting started with AWS

To get started using ZenML on the cloud, you need some basic infrastructure up 
and running which ZenML can use to run your pipelines.
This step-by-step guide explains how to set up a basic cloud stack on AWS.

{% hint style="info" %}
This guide represents **one** of many ways to create a cloud stack on AWS. 
You can customize this by adding additional components of replacing one of the 
components described in this guide.
{% endhint %}

## Prerequisites

- [Docker](https://www.docker.com/) installed and running.
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed.
- The [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) installed and authenticated.
- ZenML and the integrations for this tutorial stack installed:
    ```shell
    pip install zenml
    zenml integration install aws s3 kubernetes
    ```

## Setting up the AWS resources

All the AWS setup steps can either be done using the AWS UI or CLI. Simply select the tab for your preferred option and let's get started.
First open up a terminal which we'll use to store some values along the way which we'll need to configure our ZenML stack later.

### Artifact Store (S3 bucket)

{% tabs %}
{% tab title="AWS UI" %}

- Go to the [S3 website](https://s3.console.aws.amazon.com/s3/buckets).
- Click on `Create bucket`.
- Select a descriptive name and a region. Let's also store these values in our terminal:
    ```shell
    REGION=<REGION> # for example us-west-1
    S3_BUCKET_NAME=<S3_BUCKET_NAME>
    ```

{% endtab %}

{% tab title="AWS CLI" %}

```shell
# Set a name for your bucket and the AWS region for your resources
# Select one of the region codes for <REGION>: https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints
REGION=<REGION>  
S3_BUCKET_NAME=zenml-artifact-store

aws s3api create-bucket --bucket=$S3_BUCKET_NAME \
    --region=$REGION \
    --create-bucket-configuration=LocationConstraint=$REGION
```

{% endtab %}
{% endtabs %}

### Metadata Store (RDS MySQL database)

{% tabs %}
{% tab title="AWS UI" %}

- Go to the [RDS website](https://console.aws.amazon.com/rds).
- Make sure the correct region is selected on the top right (this region must be the same for all following steps).
- Click on `Create database`.
- Select `Easy Create`, `MySQL`, `Free tier` and enter values for your database name, username and password.
- Note down the username and password:
    ```shell
    RDS_MYSQL_USERNAME=<RDS_MYSQL_USERNAME>
    RDS_MYSQL_PASSWORD=<RDS_MYSQL_PASSWORD>
    ```
- Wait until the deployment is finished.
- Select your new database and note down its endpoint:
    ```shell
    RDS_MYSQL_ENDPOINT=<RDS_MYSQL_ENDPOINT>
    ```
- Click on the active VPC security group, select `Inbound rules` and click on `Edit inbound rules`
- Add a new rule with type `MYSQL/Aurora` and source `Anywhere-IPv4`. (**Note**: You can also restrict this to more limited IP address ranges or security groups if you want to limit access to your database.)
- Go back to your database page and click on `Modify` in the top right.
- In the `Connectivity` section, open the `Advanced configuration` and enable public access.

{% endtab %}

{% tab title="AWS CLI" %}

```shell
# Set values for the database identifier and username/password to access it
MYSQL_DATABASE_ID=zenml-metadata-store
RDS_MYSQL_USERNAME=admin
RDS_MYSQL_PASSWORD=<RDS_MYSQL_PASSWORD>

aws rds create-db-instance --engine=mysql \
    --db-instance-class=db.t3.micro \
    --allocated-storage=20 \
    --publicly-accessible \
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION \
    --master-username=$RDS_MYSQL_USERNAME \
    --master-user-password=$RDS_MYSQL_PASSWORD

# Wait until the database is created
aws rds wait db-instance-available --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION

# Fetch the endpoint
RDS_MYSQL_ENDPOINT=$(aws rds describe-db-instances --query='DBInstances[0].Endpoint.Address' \
    --output=text \
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION)

# Fetch the security group id
SECURITY_GROUP_ID=$(aws rds describe-db-instances --query='DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output=text
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION)

aws ec2 authorize-security-group-ingress \
    --protocol=tcp \
    --port=3306 \
    --cidr=0.0.0.0/0 \
    --group-id=$SECURITY_GROUP_ID \
    --region=$REGION
```

{% endtab %}
{% endtabs %}

### Container Registry (ECR)

{% tabs %}
{% tab title="AWS UI" %}

- Go to the [ECR website](https://console.aws.amazon.com/ecr).
- Make sure the correct region is selected on the top right.
- Click on `Create repository`.
- Create a private repository called `zenml-kubernetes` with default settings.
- Note down the URI of your registry:
    ```shell
    # This should be the prefix of your just created repository URI, 
    # e.g. 714803424590.dkr.ecr.eu-west-1.amazonaws.com
    ECR_URI=<ECR_URI>
    ```

{% endtab %}
{% tab title="AWS CLI" %}

```shell
aws ecr create-repository --repository-name=zenml-kubernetes --region=$REGION

REGISTRY_ID=$(aws ecr describe-registry --region=$REGION --query=registryId --output=text)
ECR_URI="$REGISTRY_ID.dkr.ecr.$REGION.amazonaws.com"
```

{% endtab %}
{% endtabs %}

### Orchestrator (EKS)

{% tabs %}
{% tab title="AWS UI" %}

- Follow [this guide](https://docs.aws.amazon.com/eks/latest/userguide/service_IAM_role.html#create-service-role) to create an Amazon EKS cluster role. We'll refer to this role as the **cluster role** in following steps.
- Follow [this guide](https://docs.aws.amazon.com/eks/latest/userguide/create-node-role.html#create-worker-node-role) to create an Amazon EC2 node role. We'll refer to this role as the **node role** in following steps.
- Go to the [IAM website](https://console.aws.amazon.com/iam), select `Roles` and edit the **node role** role.
- Click on `Add permissions` and select `Attach policies`.
- Attach the `SecretsManagerReadWrite`, and `AmazonS3FullAccess` policies to the role. The node role should now have the following attached policies: `AmazonEKSWorkerNodePolicy`, `AmazonEC2ContainerRegistryReadOnly`, `AmazonEKS_CNI_Policy`, `SecretsManagerReadWrite` and `AmazonS3FullAccess`.
- Go to the [EKS website](https://console.aws.amazon.com/eks).
- Make sure the correct region is selected on the top right.
- Click on `Add cluster` and select `Create`.
- Enter a name and select the **cluster role** for `Cluster service role`.
- Keep the default values for the networking and logging steps and create the cluster.
- Note down the cluster name:
    ```shell
    EKS_CLUSTER_NAME=<EKS_CLUSTER_NAME>
    ```
- After the cluster is created, select it and click on `Add node group` in the `Compute` tab.
- Enter a name and select the **node role**.
- Keep all other default values and create the node group.

{% endtab %}

{% tab title="AWS CLI" %}

```shell
# Choose names for your EKS cluster, node group and their respective roles
EKS_CLUSTER_NAME=zenml-eks-cluster
NODEGROUP_NAME=zenml-eks-cluster-nodes
EKS_ROLE_NAME=ZenMLEKSRole
EC2_ROLE_NAME=ZenMLEKSNodeRole

EKS_POLICY_JSON='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
aws iam create-role \
    --role-name=$EKS_ROLE_NAME \
    --assume-role-policy-document="$EKS_POLICY_JSON"
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKSClusterPolicy' \
    --role-name=$EKS_ROLE_NAME


EC2_POLICY_JSON='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
aws iam create-role \
    --role-name=$EC2_ROLE_NAME \
    --assume-role-policy-document="$EC2_POLICY_JSON"
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/SecretsManagerReadWrite' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonS3FullAccess' \
    --role-name=$EC2_ROLE_NAME


# Get the role ARN's
EKS_ROLE_ARN=$(aws iam get-role --role-name=$EKS_ROLE_NAME --query='Role.Arn' --output=text)
EC2_ROLE_ARN=$(aws iam get-role --role-name=$EC2_ROLE_NAME --query='Role.Arn' --output=text)


# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters='Name=is-default,Values=true' \
    --query='Vpcs[0].VpcId' \
    --output=text \
    --region=$REGION)

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets --region=$REGION \
    --filters="Name=vpc-id,Values=$VPC_ID" \
    --query='Subnets[*].SubnetId' \
    --output=json)

aws eks create-cluster --region=$REGION \
    --name=$EKS_CLUSTER_NAME \
    --role-arn=$EKS_ROLE_ARN \
    --resources-vpc-config="{\"subnetIds\": $SUBNET_IDS}"

# Wait until the cluster is active
aws eks wait cluster-active --name=$EKS_CLUSTER_NAME \
    --region=$REGION

aws eks create-nodegroup --region=$REGION \
    --cluster-name=$EKS_CLUSTER_NAME \
    --nodegroup-name=$NODEGROUP_NAME \
    --node-role=$EC2_ROLE_ARN \
    --subnets="$SUBNET_IDS"

# Wait until the node group is active
aws eks wait nodegroup-active --cluster-name=$EKS_CLUSTER_NAME \
    --nodegroup-name=$NODEGROUP_NAME \
    --region=$REGION
```

{% endtab %}
{% endtabs %}

## Register the ZenML stack

- Register the artifact store:
    ```shell
    zenml artifact-store register s3_store \
        --flavor=s3 \
        --path=s3://$S3_BUCKET_NAME
    ```

- Register the container registry and authenticate your local docker client
    ```shell    
    zenml container-registry register ecr_registry \
        --flavor=aws \
        --uri=$ECR_URI

    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI
    ```

- Register the metadata store:
    ```shell
    zenml metadata-store register rds_mysql \
        --flavor=mysql \
        --database=zenml \
        --secret=rds_authentication \
        --host=$RDS_MYSQL_ENDPOINT
    ```

- Register the secrets manager:
    ```shell
    zenml secrets-manager register aws_secrets_manager \
        --flavor=aws \
        --region_name=$REGION
    ```

- Configure your `kubectl` client and register the orchestrator:
    ```shell
    aws eks --region=$REGION update-kubeconfig --name=$EKS_CLUSTER_NAME
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
        --user=$RDS_MYSQL_USERNAME \
        --password=$RDS_MYSQL_PASSWORD
    ```

After all of this setup, you're now ready to run any ZenML pipeline on AWS!

## Quick setup

If you're looking for a way to get started quickly, we've combined all the commands so you can copy-paste them and execute them in a single go. You'll only need to set values for the `<REGION>` and `<RDS_MYSQL_PASSWORD>` right at the beginning before executing the rest.

<details>
    <summary>Quick setup commands</summary>

```shell
# Select one of the region codes for <REGION>: https://docs.aws.amazon.com/general/latest/gr/rande.html#regional-endpoints
REGION=<REGION>  
# Choose a secure password for your database admin account. Make sure it includes:
# - at least 8 printable ASCII characters
# - no slash, single or double quotes or @ signs
RDS_MYSQL_PASSWORD=<RDS_MYSQL_PASSWORD>

# Other parameters (we've set some defaults for these but feel free to change them):
S3_BUCKET_NAME=zenml-artifact-store
MYSQL_DATABASE_ID=zenml-metadata-store
RDS_MYSQL_USERNAME=admin
EKS_CLUSTER_NAME=zenml-eks-cluster
NODEGROUP_NAME=zenml-eks-cluster-nodes
EKS_ROLE_NAME=ZenMLEKSRole
EC2_ROLE_NAME=ZenMLEKSNodeRole


aws s3api create-bucket --bucket=$S3_BUCKET_NAME \
    --region=$REGION \
    --create-bucket-configuration=LocationConstraint=$REGION

aws rds create-db-instance --engine=mysql \
    --db-instance-class=db.t3.micro \
    --allocated-storage=20 \
    --publicly-accessible \
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION \
    --master-username=$RDS_MYSQL_USERNAME \
    --master-user-password=$RDS_MYSQL_PASSWORD

# Wait until the database is created
aws rds wait db-instance-available --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION

# Fetch the endpoint
RDS_MYSQL_ENDPOINT=$(aws rds describe-db-instances --query='DBInstances[0].Endpoint.Address' \
    --output=text \
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION)

# Fetch the security group id
SECURITY_GROUP_ID=$(aws rds describe-db-instances --query='DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
    --output=text
    --db-instance-identifier=$MYSQL_DATABASE_ID \
    --region=$REGION)

aws ec2 authorize-security-group-ingress \
    --protocol=tcp \
    --port=3306 \
    --cidr=0.0.0.0/0 \
    --group-id=$SECURITY_GROUP_ID \
    --region=$REGION

aws ecr create-repository --repository-name=zenml-kubernetes --region=$REGION

REGISTRY_ID=$(aws ecr describe-registry --region=$REGION --query=registryId --output=text)
ECR_URI="$REGISTRY_ID.dkr.ecr.$REGION.amazonaws.com"

EKS_POLICY_JSON='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "eks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
aws iam create-role \
    --role-name=$EKS_ROLE_NAME \
    --assume-role-policy-document="$EKS_POLICY_JSON"
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKSClusterPolicy' \
    --role-name=$EKS_ROLE_NAME


EC2_POLICY_JSON='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'
aws iam create-role \
    --role-name=$EC2_ROLE_NAME \
    --assume-role-policy-document="$EC2_POLICY_JSON"
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/SecretsManagerReadWrite' \
    --role-name=$EC2_ROLE_NAME
aws iam attach-role-policy \
    --policy-arn='arn:aws:iam::aws:policy/AmazonS3FullAccess' \
    --role-name=$EC2_ROLE_NAME


# Get the role ARN's
EKS_ROLE_ARN=$(aws iam get-role --role-name=$EKS_ROLE_NAME --query='Role.Arn' --output=text)
EC2_ROLE_ARN=$(aws iam get-role --role-name=$EC2_ROLE_NAME --query='Role.Arn' --output=text)


# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters='Name=is-default,Values=true' \
    --query='Vpcs[0].VpcId' \
    --output=text \
    --region=$REGION)

# Get subnet IDs
SUBNET_IDS=$(aws ec2 describe-subnets --region=$REGION \
    --filters="Name=vpc-id,Values=$VPC_ID" \
    --query='Subnets[*].SubnetId' \
    --output=json)

aws eks create-cluster --region=$REGION \
    --name=$EKS_CLUSTER_NAME \
    --role-arn=$EKS_ROLE_ARN \
    --resources-vpc-config="{\"subnetIds\": $SUBNET_IDS}"

# Wait until the cluster is active
aws eks wait cluster-active --name=$EKS_CLUSTER_NAME \
    --region=$REGION

aws eks create-nodegroup --region=$REGION \
    --cluster-name=$EKS_CLUSTER_NAME \
    --nodegroup-name=$NODEGROUP_NAME \
    --node-role=$EC2_ROLE_ARN \
    --subnets="$SUBNET_IDS"

# Wait until the node group is active
aws eks wait nodegroup-active --cluster-name=$EKS_CLUSTER_NAME \
    --nodegroup-name=$NODEGROUP_NAME \
    --region=$REGION

# ZenML stack setup
zenml artifact-store register s3_store \
    --flavor=s3 \
    --path=s3://$S3_BUCKET_NAME

zenml container-registry register ecr_registry \
    --flavor=aws \
    --uri=$ECR_URI

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

zenml metadata-store register rds_mysql \
    --flavor=mysql \
    --database=zenml \
    --secret=rds_authentication \
    --host=$RDS_MYSQL_ENDPOINT

zenml secrets-manager register aws_secrets_manager \
    --flavor=aws \
    --region_name=$REGION

aws eks --region=$REGION update-kubeconfig --name=$EKS_CLUSTER_NAME
kubectl create namespace zenml

zenml orchestrator register eks_kubernetes_orchestrator \
    --flavor=kubernetes \
    --kubernetes_context=$(kubectl config current-context)

zenml stack register kubernetes_stack \
        -o eks_kubernetes_orchestrator \
        -a s3_store \
        -m rds_mysql \
        -c ecr_registry \
        -x aws_secrets_manager \
        --set

zenml secret register rds_authentication \
        --schema=mysql \
        --user=$RDS_MYSQL_USERNAME \
        --password=$RDS_MYSQL_PASSWORD
```
</details>