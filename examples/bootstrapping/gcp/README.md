# Bootstrapping GCP

This is an easy, friction-less approach to bootstrap your Google Cloud Account with all required resources to run ZenML.

## Prerequisites

Thanks to [Terraform](https://terraform.io), this is a straight-forward affair:

- You'll need a [Google Cloud Account](https://cloud.google.com)
- You need the [`gcloud`-CLI installed](https://cloud.google.com/sdk/docs/install) and be logged in
- You need [Terraform installed](https://learn.hashicorp.com/tutorials/terraform/install-cli)

That's it.

## What this script will do

Before anyone runs anything from anywhere, it should be clear to what will happen - especially since this bootstrapping will incur cost on your GCP project. 
Let me walk you through the ins-and-outs. When you execute this bootstrapping script, it will:

1. Create a custom role within your Google Cloud Project, with the required permissions attached.
2. A service account for ZenML, automatically associated with the custom role.
3. A Cloud SQL MySQL instance as the ZenML metadata store.
4. A Google Storage Bucket as the ZenML artifact store.
5. A Kubernetes cluster for your pipelines.
6. A Kubernetes service to establish connectivity between the cluster and the metadata store.
7. A shell script to provision your local environment with the newly created resources:
    - starts a proxy to securely communicate with the metadata store
    - configures the metadata and artifact store for your local ZenML project

## Running the bootstrapping

The actual bootstrapping is broken into two simple main steps:

1. Running the Terraform script.
2. Configure your local ZenML project with the new resources.

### 1. Terraform

While the bootstrapping can take up to 10 minutes to complete, executing the Terraform script is pretty straight-forward.

0. Navigate to the bootstrapping example folder: 
```bash
cd ./examples/bootstrapping/gcp
```
1. Initialize Terraform: 
```bash
terraform init
```
2. (Optional) Plan the execution to see what will be created: 
```bash
terraform plan
```
3. Execute the Terraform script: 
```bash
terraform apply
```

The script will output all kinds of helpful details and command line helpers, e.g. a oneliner to launch a proxy to the metadata store, commands to configure ZenML and other information. 

If you're just experimenting, you can destroy all created resources by running:
```bash
terraform destroy
```

### 2. ZenML

Once you've successfully completed the Terraform bootstrapping, a `setup.sh`-file will be created for you. This file will establish a connection to the metadata store and configure ZenML with the right credentials to run future pipelines on your newly created Cloud resources.
To run it, navigate to the root of your project and run:
```bash
./examples/bootstrapping/gcp/setup.sh
```

Congratz, you've bootstrapped your Google Cloud account to work seamlessly with ZenML.