---
description: A guide on how to deploy ZenML
---

# Deploy ZenML

### The components of a ZenML Deployment

A ZenML deployment typically consist of the following components:

* A FastAPI HTTP server that exposes a RESTful API and serves the Dashboard.
* An SQL database as the backend to track configurations and metadata.
* An optional external secrets management service that is used as a backend for the ZenML secrets store.

ZenML relies on a SQLAlchemy-compatible database to store all its data: stack configurations, pipeline runs etc. The location and type of this database can be configured by the user. By default, an SQLite database on local host is used. For production settings MySQL should be used.

The following diagram shows how such a deployment is used when a pipeline run is triggered from a client machine.

<figure><img src="../../../.gitbook/assets/Remote_with_secrets_manager.png" alt=""><figcaption></figcaption></figure>

### Deploying ZenML in the Cloud: Remote Deployment of the HTTP server and Database

For a lot of use cases like sharing stacks and pipeline information with your team and for using cloud services to run your pipelines, you have to deploy ZenML in the cloud.

Your ZenML code interacts with the server across different concerns. For example,

* your local machine connects to the server to read and write the stack configurations to allow collaboration.
* the individual orchestrators and step operators communicate with the server to write and track your pipeline run data.
* the dashboard is served from the server to give a UI interface to all of your metadata.
* the ZenML server also acts as a central point of access for managing secrets.

As such, it is important that you deploy ZenML in a way that is accessible from your machine as well as from all stack components that need access to the server.

> If you are looking for a quick deployment without having to worry about configuring the right access, the [`zenml deploy` CLI command ](cli.md)is the way to go!

#### Scenario 3: Server and Database hosted on cloud

This is similar to Scenario 2, with the difference that both the HTTP server and the database are running remotely rather than on your local machine. This is how you can unleash the real collaborative power of ZenML. With this type of deployment, stacks and pipeline runs can be shared with other users across larger teams and organizations. If you are using cloud, or shared on-premise services to run your pipelines, such as Kubeflow, GitHub, Spark, Vertex AI, AWS Sagemaker or AzureML, a centralized shared ZenML Server is also the recommended deployment strategy for ZenML, because these services will need to communicate with the ZenML server.

When deploying the ZenML server in the cloud, you may also opt to use a cloud secrets management back-end like the AWS Secrets Manager, GCP Secrets Manager or Azure Key Vault to store your secrets. This is the recommended way to store your secrets in production. The ZenML server will act as a proxy for all secrets related requests, which means that the chosen secrets store back-end is not visible to the ZenML client.

The diagram below shows the architecture: both the server and database are remote and can be provisioned and managed independently. The server takes the connection details of the database as one of its inputs and that's how they work together. You can refer to the deployment options pages, to see how it's done in each case. Using a cloud deployment enables you to collaborate with your team members by sharing stacks and having visibility into the pipelines run by your team. This new paradigm will also evolve to include more advanced access control features that you can use to manage the roles and responsibilities of everyone in your team through the ZenML Server.

![ZenML with remote server and DB](../../assets/getting\_started/Scenario3.2.png)

Such a remote deployment unlocks ZenML to its full potential as the MLOps hub within your production stacks. The diagram below visualizes how a pipeline is run through a deployed ZenML Server with a remote orchestrator, artifact store and container registry.

![Remote Stack](../../assets/diagrams/RemoteServer.png)

You can use any of the following ways to get started:

* The [`zenml deploy` CLI command](cli.md) that provides an easy interface to deploy on Kubernetes in AWS, GCP or Azure.
* A [Docker image](docker.md) that you can run in any environment of your choice.
* A [Helm chart](helm.md) that can be deployed to any Kubernetes cluster (on-prem or managed).

In the following pages, we take a look at each of those options.
