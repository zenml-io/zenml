# Stack Component Deploy/Destroy Imp things to know

## Deploying Stack Components

- You can deploy stack components directly using the new `deploy` subcommand.
- The command takes in a name to use for the stack component, along with the flavor and the cloud provider. In case of components like artifact stores and container registries, the cloud is the same as the flavor and can be omitted from the command.

For example, to deploy an S3 artifact store, you can run:

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3
```

- Currently, only gcp, aws and k3d are supported as providers.
- Available flavors:
    Experiment Trackers:
    - `mlflow`
    Model Deployers:
    - `seldon`
    - `kserve`
    Artifact Stores:
    - `s3`
    - `gcs`
    - `minio`
    Container Registries:
    - `gcr`
    - `ecr`
    - `k3d-registry`
    Orchestrators:
    - `kubernetes`
    - `kubeflow`
    - `tekton`
    - `sagemaker`
    Step Operators:
    - `sagemaker`
    Secrets Managers:
    - `aws`
    - `gcp`

## Customizing the deployment of stack components

- You can pass configuration specific to the stack components as key-value arguments. Here are all the config values that can be passed. If you don't provide a name, a random one is generated for you.

To assign an existing bucket to the mlflow experiment tracker, you can run:

```bash
zenml experiment-tracker deploy mlflow_tracker --flavor=mlflow --mlflow_bucket=gs://my_bucket
```
For an artifact store, you can pass bucket_name as the argument to the command.

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --bucket_name=my_bucket
```
For container registries you can pass the repository name using repo_name

```bash
zenml container-registry deploy aws_registry --flavor=aws --repo_name=my_repo
```

This is only useful for the AWS case since AWS requires a repository to be created before pushing images to it and the deploy command ensures that a repository with the name you provide is created.

In case of GCP and other providers, you can choose the repository name while pushing the image, in code. This is achieved through setting the `target_repo` attribute of the `DockerSettings` object (TODO attach link).


- You can also pass a region to deploy your resources to, in the case of AWS and GCP recipes. For example, to deploy an S3 artifact store in the us-west-2 region, you can run:

```bash
zenml artifact-store deploy s3_artifact_store --flavor=s3 --region=us-west-2
```

The default region is eu-west-1 for AWS and us-central1 for GCP.

- In the case of gcp components, it is *required* that you pass a project ID to the command, for the first time you're creating any gcp resource. The command will remember the project ID for subsequent calls. For example, to deploy a GCS artifact store, you can run:

```bash
zenml artifact-store deploy gcs_artifact_store --flavor=gcs --project_id=my_project
```

## Destroying Stack Components

You can destroy a stack component using the `destroy` subcommand. For example, to destroy the S3 artifact store you created above, you can run:

```bash
zenml artifact-store destroy s3_artifact_store
```
