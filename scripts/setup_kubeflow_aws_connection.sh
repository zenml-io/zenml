#!/usr/bin/env bash

set -e

export AWS_REGION="us-east-1"
export AWS_EKS_CLUSTER="zenhacks-cluster"
export ECR_REGISTRY_NAME="715803424590.dkr.ecr.us-east-1.amazonaws.com"
export S3_BUCKET_NAME="s3://zenbytes-bucket"
export KUBEFLOW_NAMESPACE="kubeflow"
export KUBE_CONTEXT="zenml-eks"

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY_NAME
aws eks --region $AWS_REGION update-kubeconfig --name $AWS_EKS_CLUSTER --alias $KUBE_CONTEXT

# Register container registry
zenml container-registry register ecr_registry --flavor=default --uri=$ECR_REGISTRY_NAME

# Register orchestrator (Kubeflow on AWS)
zenml orchestrator register eks_orchestrator --flavor=kubeflow --kubernetes_context=$KUBE_CONTEXT --synchronous=True

# Register metadata store and artifact store
zenml metadata-store register kubeflow_metadata_store --flavor=kubeflow
zenml artifact-store register s3_store --flavor=s3 --path=$S3_BUCKET_NAME

# Register a secret manager
zenml secrets-manager register aws_secret_manager --flavor=aws

# Register the aws_kubeflow_stack
zenml stack register aws_kubeflow_stack -m kubeflow_metadata_store -a s3_store -o eks_orchestrator -c ecr_registry \
   -x aws_secret_manager

# Set the stack
zenml stack set aws_kubeflow_stack
zenml stack describe
zenml stack up