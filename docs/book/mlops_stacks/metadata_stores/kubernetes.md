---
description: Deploy a Kubernetes MySQL database service and use it to store metadata information
---

The Kubernetes Metadata Store is a spin off the [MySQL Metadata Store](./mysql.md)
provided with the Kubernetes ZenML integration. In addition to functioning
like a regular MySQL Metadata Store, it is also able to automatically provision
a MySQL database service on top of a Kubernetes cluster and connect to it.

## When would you want to use it?

You should use the Kubernetes Metadata Store if you have access to a Kubernetes
cluster and are looking for a quick and convenient way to provision and
configure a Metadata Store that can be used to share your pipeline information
with other members of your team or organization. A quick way to get you started
using ZenML in a collaborative setting, if you have access to a Kubernetes
cluster, is to use the Kubernetes Metadata Store and the [Kubernetes Orchestrator](../orchestrators/kubernetes.md)
together in the same stack. 

The Kubernetes Metadata Store is not suited for production use because it
lacks the scalability, performance and maintainability required from a
production MLOps stack.

You should consider one of the other [Metadata Store flavors](./overview.md#metadata-store-flavors)
if you don't have access to a Kubernetes cluster or if you wish to use an
alternative that is better suited for production.

## How do you deploy it?

The Kubernetes Metadata Store flavor is provided by the Kubernetes ZenML
integration, you need to install it on your local machine to be able to register
a Kubernetes Metadata Store and add it to your stack:

```shell
zenml integration install kubernetes -y
```

This guide also assumes you have already installed [the `kubectl` utility](https://kubernetes.io/docs/tasks/tools/#kubectl)
on your machine and have configured access to a Kubernetes cluster using a
[kubectl config context](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/).
With the kubectl configuration context name on hand, registering a Kubernetes
Metadata Store and using it in a stack can be done as follows:

```shell
# Register the Kubernetes metadata store
zenml metadata-store register k8s_metadata_store --flavor=kubernetes \
    --deployment_name=mysql \
    --kubernetes_context==<kubernetes-context-name> \
    --kubernetes_namespace=zenml

# Register and set a stack with the new metadata store
zenml stack register k8s_stack -m k8s_metadata_store  ... --set

# Run `zenml stack up` to deploy the MySQL database service and forward the
# MySQL port locally
zenml stack up
```

The `zenml stack up` command must be run locally to deploy the MySQL database
service in the remote Kubernetes cluster and to forward the MySQL service port
locally.

For more, up-to-date information on the Kubernetes Metadata Store implementation
and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubernetes.metadata_stores.kubernetes_metadata_store).

## How do you use it?

Aside from the fact that the metadata information is stored using a MySQL
database deployed in a Kubernetes cluster, using the Kubernetes Metadata Store
is no different than [using any other flavor of Metadata Store](./overview.md#how-to-use-it).

You can also check out our examples pages for working examples that use the
Kubernetes Metadata Store in their stacks:

- [Pipeline Orchestration on Kubernetes](https://github.com/zenml-io/zenml/tree/main/examples/kubernetes_orchestration)
