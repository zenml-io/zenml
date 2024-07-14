# Assisted ZenML Stack Deployment

These are a set of scripts that can be used to provision infrastructure for **ZenML stacks directly in your browser** in AWS and GCP with minimal user input. The scripts are used by the ZenML CLI and dashboard stack deployment feature to not only provision the infrastructure but also to configure the ZenML stack, components and service connectors with the necessary credentials.

## AWS

A Cloud Formation template is used to provision the infrastructure in AWS. The template is parameterized and the user is prompted to provide the necessary values during the CLI / dashboard deployment process. The values are embedded in a Cloud Formation template creation URL that the user can follow to deploy the stack.

Files:

* [aws/aws-ecr-s3-sagemaker.yaml](aws/aws-ecr-s3-sagemaker.yaml): Cloud Formation template for provisioning ECR and S3 resources along with a IAM user, IAM role and AWS secret key. The template also uses a Lambda function to register the ZenML stack with the ZenML server.

The Cloud Formation template is uploaded to AWS S3 using a GitHub action during the release process at the following location: https://zenml-cf-templates.s3.eu-central-1.amazonaws.com/aws-ecr-s3-sagemaker.yaml

## GCP

A Deployment Manager template is used to provision the infrastructure in GCP. The template is parameterized and the user is prompted to provide the necessary values during the CLI / dashboard deployment process. Given that there is no way to trigger a Deployment Manager template creation directly using a URL, a GCP Cloud Shell session is opened instead and the user is provided with a set of configuration values that they have to manually copy and paste into the deployment script.

Files:

* [gcp/gcp-gar-gcs-vertex.jinja](gcp/gcp-gar-gcs-vertex.jinja): Deployment Manager template for provisioning GCS and GCR resources along with a GCP service account and credentials. The template also uses a Cloud Function instance to register the ZenML stack with the ZenML server.
* [gcp/main.py](gcp/main.py): The Python script that is used by the Cloud Function instance to register the ZenML stack with the ZenML server. The script is triggered by a Cloud Function call that is sent by the Deployment Manager template after the stack resources have been provisioned.
* [gcp/gcp-gar-gcs-vertex-deploy.sh](gcp/gcp-gar-gcs-vertex-deploy.sh): Deployment script that the user must run in the Cloud Shell to deploy the stack. In addition to deploying the Deployment Manager template, the script also takes care of enabling the necessary GCP APIs and configuring the necessary permissions for the various service accounts involved.
* [gcp/gcp-gar-gcs-vertex.md](gcp/gcp-gar-gcs-vertex.md): A markdown file that provides the user with instructions on how to deploy the stack using the deployment script. This is powered by the tutorial walkthrough feature in the Google Cloud Shell.

The Cloud Function script is uploaded to GCP GCS using a GitHub action during the release process at the following location: gs://zenml-public-bucket/zenml-gcp-dm-templates/gcp-dm-stack-register.zip
