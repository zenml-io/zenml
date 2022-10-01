---
description: Deploying ZenML on cloud using Docker or Helm
---

If you wish to deploy ZenML on clouds other than AWS, Azure and GCP or on any other resource like a serverless platform or an on-prem Kubernetes cluster, you have two options:

- Using a Docker container.
- Using the Helm chart.

## Using Docker

The ZenML server image is available at `zenmldocker/zenml-server` and can be used in container services, serverless platforms like [Cloud Run](https://cloud.google.com/run), [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview) and more!

You can also run this image locally using the `up` command and the `--docker` flag.

```
zenml up --docker
```

## Using Helm

The ZenML repository hosts a Helm chart that can be used to deploy to Kubernetes. This chart is not hosted on an online repository yet and so you can follow the steps below:

- Clone the `zenml-io/zenml` repository.

    ```
    git clone https://github.com/zenml-io/zenml.git
    ```
- Go into the directory that hosts the chart.

    ```
    cd src/zenml/zen_server/deploy/helm/
    ```

- Take a look at the `values.yaml` file to configure settings for your ZenML deployment. Make sure you have a MySQL database to use with the server and fill the `zenml.database` map with its values.

- Once everything is configured, you can now run the following command to create a release.
    ```
    helm -n <KUBERNETES_NAMESPACE> --create-namespace install zenml-server . 
    ```

> **Note**
> You will need to have an existing Kubernetes cluster and `kubectl` installed and configured, in addition to having `helm` itself.