---
description: Setting up your stack on Amazon Web Services (AWS)
---

AWS is one of the most popular cloud providers and offers a range of services that can be used while building your MLOps stacks. You can learn more about machine learning at AWS on their [website](https://aws.amazon.com/machine-learning/).

# Available Stack Components

This is a list of all supported AWS services that you can use as ZenML stack components.
## Elastic Kubernetes Service (EKS)

Amazon Elastic Kubernetes Service (Amazon EKS) is a managed container service to run and scale Kubernetes applications in the cloud or on-premises. [Learn more here](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html).

* An EKS cluster can be used to run multiple **orchestrators**.
    * [A Kubernetes-native orchestrator.](../../mlops_stacks/orchestrators/kubernetes.md)
    * [A Kubeflow orchestrator.](../../mlops_stacks/orchestrators/kubeflow.md)
* You can host **model deployers** on the cluster.
    * [A Seldon model deployer.](../../mlops_stacks/model_deployers/seldon.md)
    * [An MLflow model deployer.](../../mlops_stacks/model_deployers/mlflow.md)
* Experiment trackers can also be hosted on the cluster.
    * [An MLflow experiment tracker](../../mlops_stacks/experiment_trackers/mlflow.md)

## Simple Storage Service (S3)

Amazon Simple Storage Service (Amazon S3) is an object storage service that offers scalability, data availability, security, and performance. [Learn more here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html).

* You can use an [S3 bucket as an artifact store](../../mlops_stacks/artifact_stores/amazon_s3.md) to hold files from our pipeline runs like models, data and more. 

## Elastic Container Registry (ECR)

Amazon Elastic Container Registry (Amazon ECR) is an AWS managed container image registry service that is secure, scalable, and reliable. [Learn more here](https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html).

* An [ECS registry can be used as a container registry](../../mlops_stacks/container_registries/amazon_ecr.md) stack component to host images of your pipelines. 

## Sagemaker

Amazon SageMaker is a fully managed machine learning service. With SageMaker, data scientists and developers can quickly build and train machine learning models, and then directly deploy them into a production-ready hosted environment. [Learn more here](https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html).

* You can use [Sagemaker as a step operator](../../mlops_stacks/step_operators/amazon_sagemaker.md) to run specific steps from your pipeline using it as the backend.

## Relational Database Service (RDS)

Amazon Relational Database Service (Amazon RDS) is a web service that makes it easier to set up, operate, and scale a relational database in the AWS Cloud. [Learn more here](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html).

* You can use [Amazon RDS as a metadata store](../../mlops_stacks/metadata_stores/mysql.md) to track metadata from your pipeline runs.

## Secrets Manager

Secrets Manager enables you to replace hardcoded credentials in your code, including passwords, with an API call to Secrets Manager to retrieve the secret programmatically. [Learn more here](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html).

* You can store your secrets to be used inside a pipeline by registering the [AWS Secrets Manager as a ZenML secret manager](../../mlops_stacks/secrets_managers/amazon_aws.md) stack component.

In the following pages, you will find step-by-step guides for setting up some common stacks using the AWS console and the CLI. More combinations and components are progressively updated in the form of new pages.
