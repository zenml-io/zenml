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

Write here about the options to deploy a docker image generally