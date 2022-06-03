#!/usr/bin/env bash

set -e

export AWS_REGION="us-east-1"
export AWS_EKS_CLUSTER="zenhacks-cluster"
export ECR_REGISTRY_NAME="715803424590.dkr.ecr.us-east-1.amazonaws.com"
export KUBE_CONTEXT="zenml-eks"

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY_NAME
aws eks --region $AWS_REGION update-kubeconfig --name $AWS_EKS_CLUSTER --alias $KUBE_CONTEXT
