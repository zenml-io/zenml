---
description: Setting up your stack on Amazon Web Services (AWS)
---

AWS is one of the most popular cloud providers and offers a range of services that can be used while building your MLOps stacks. You can learn more machine learning at AWS on their [website](https://aws.amazon.com/machine-learning/).

# Available Stack Components

This is a list of all supported AWS services that you can use as ZenML stack components.
## Elastic Kubernetes Service (EKS)

* An EKS cluster can be used to run multiple **orchestrators**.
    * [A Kubernetes-native orchestrator.](../../mlops_stacks/orchestrators/kubernetes.md)
    * [A Kubeflow orchestrator.](../../mlops_stacks/orchestrators/kubeflow.md)
* You can host **model deployers** on the cluster.
    * [A Seldon model deployer.](../../mlops_stacks/model_deployers/seldon.md)
    * [An MLflow model deployer.](../../mlops_stacks/model_deployers/mlflow.md)
* Experiment trackers can also be hosted on the cluster.
    * [An MLflow experiment tracker](../../mlops_stacks/experiment_trackers/mlflow.md)

## Simple Storage Service (S3)

* You can use an [S3 bucket as an artifact store](../../mlops_stacks/artifact_stores/amazon_s3.md) to hold files from our pipeline runs like models, data and more. 

## Elastic Container Registry (ECR)

* An [ECS registry can be used as a container registry](../../mlops_stacks/container_registries/amazon_ecr.md) stack component to host images of your pipelines. 

## Sagemaker

* You can use [Sagemaker as a step operator](../../mlops_stacks/step_operators/amazon_sagemaker.md) to run specific steps from your pipeline using it as the backend.

## Relational Database Service (RDS)

* You can use [Amazon RDS as a metadata store](../../mlops_stacks/metadata_stores/mysql.md) to track metadata from your pipeline runs.

## Secrets Manager

* You can store your secrets to be used inside a pipeline by registering the [AWS Secrets Manager as a ZenML secret manager](../../mlops_stacks/secrets_managers/amazon_aws.md) stack component.

In the following pages, you will find step-by-step guides for setting up some common stacks using the AWS console and the CLI. More combinations and components are progressively updated in the form of new pages.
