---
description: Deploying ZenML on the Cloud
---

# Deploying ZenML

All of the metadata about your pipelines and stacks in ZenML is stored in a centralized manner within a ZenML server. A ZenML server can exist locally on your machine or deployed on a cloud of your choice. 
## ZenML On your local machine

You can setup ZenML locally through the use of the `up` command.

```
zenml up
```

This sets up a local daemon (with options to run it as a Docker container) that is backed by a SQLite store on your machine. You also get an URL to access the ZenML Dashboard which shows your available stacks, pipeline runs and team settings among other things.

// TODO: ADD SCREENSHOT OF DASHBOARD

## ZenML on the Cloud

Running ZenML locally is an easy way to experiment with your pipelines and design proof-of-concepts. However, for a lot of use cases like: sharing stacks and pipeline information with your team and for using cloud services to run your pipelines, you have to deploy ZenML on the cloud.

You can use any of the following ways to get started:
- The `zenml deploy` CLI command that provides an easy interface to deploy on Kubernetes in AWS, GCP or Azure.
- A Docker image that you can run in any environment of your choice.
- A Helm chart that can be deployed to any Kubernetes cluster (on-prem or managed).

In the following sections, let's take a look at each of those options.

