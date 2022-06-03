#!/usr/bin/env bash

set -e

export AWS_REGION="us-east-1"
export AWS_EKS_CLUSTER="zenhacks-cluster"
export ECR_REGISTRY_NAME="715803424590.dkr.ecr.us-east-1.amazonaws.com"
export KUBE_CONTEXT="zenml-eks"

docker login --username AWS -p $(aws ecr get-login-password --region us-east-1) 715803424590.dkr.ecr.us-east-1.amazonaws.com
aws eks --region $AWS_REGION update-kubeconfig --name $AWS_EKS_CLUSTER --alias $KUBE_CONTEXT
