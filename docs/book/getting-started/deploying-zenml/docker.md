---
description: Deploying ZenML on cloud using Docker or Helm
---

If you wish to deploy ZenML on clouds other than AWS, Azure and GCP or on any other resource like a serverless platform or an on-prem Kubernetes cluster, you have two options:

- Using a Docker container.
- Using the Helm chart.

## Using Docker

The ZenML server image is available at `zenmldocker/zenml-server` and can be used in container services, serverless platforms like [Cloud Run](https://cloud.google.com/run), [Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview) and more!


* Configure settings for your deployment, by doing/setting these ENV variables.
* Now, run the image using the following command:
    ```
    docker run ...
    ```
* You can check the logs of the container to verify if the server is up and depending on where you have deployed it, you can also access the dashboard at a `localhost` port (if running locally) or through some other service that exposes your container to the internet. 

### Running locally
You can also run this image locally using the `up` command and the `--docker` flag.

```
zenml up --docker
```
