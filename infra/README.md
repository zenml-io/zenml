# Assisted ZenML Stack Deployment

These are a set of scripts that can be used to provision infrastructure for **ZenML stacks directly in your browser** in AWS and GCP with minimal user input. The scripts are designed to be run with a single click and will deploy the ZenML stack in your AWS or GCP account.

## Deploy a full ZenML Stack on AWS

Click the button below to deploy a ZenML stack in your AWS account using AWS Cloud Formation. Log in to AWS and follow the instructions in the Cloud Formation console to deploy the stack.

[![Launch Stack](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/create/review?stackName=zenml-stack&templateURL=https://zenml-cf-templates.s3.eu-central-1.amazonaws.com/aws-ecr-s3-sagemaker.yaml)


## Deploy a full ZenML Stack on GCP

Click the button below to deploy a ZenML stack on your GCP project using Google Cloud Shell. Google Cloud Shell will open and clone this repository. Follow the instructions in the Cloud Shell terminal to deploy the stack.

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://ssh.cloud.google.com/cloudshell/editor?ephemeral=true&cloudshell_git_repo=https://github.com/zenml-io/zenml&cloudshell_workspace=infra/gcp&cloudshell_open_in_editor=gcp-gar-gcs-vertex.jinja,gcp-gar-gcs-vertex-deploy.sh&cloudshell_tutorial=gcp-gar-gcs-vertex.md&cloudshell_git_branch=feature/prd-482-gcp-stack-deployment)

