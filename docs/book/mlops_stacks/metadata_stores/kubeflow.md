---
description: Use the Kubeflow ML metadata service to store ML metadata 
---

Kubeflow deployments include a [ML metadata service](https://www.kubeflow.org/docs/components/pipelines/concepts/metadata/)
that is compatible with ZenML. The Kubeflow Metadata Store is a
[Metadata Store](./overview.md) flavor provided with the Kubeflow ZenML
integration that uses [the Kubeflow ML metadata service](https://www.kubeflow.org/)
to store metadata information.

## When would you want to use it?

The Kubeflow Metadata Store can only be used in conjunction with the [Kubeflow Orchestrator](../orchestrators/kubeflow.md).

You should use the Kubeflow Metadata Store if you already use a Kubeflow
Orchestrator in your stack and if you wish to reuse the Kubeflow ML metadata
service as a backend for your Metadata Store. This is a convenient way to avoid
having to deploy and manage additional services such as a MySQL database for
your Metadata Store. However, this will put additional strain on your Kubeflow
ML metadata service and you may have to resize it accordingly.

You should consider one of the other [Metadata Store flavors](./overview.md#metadata-store-flavors)
if you don't use a Kubeflow Orchestrator in your stack, or if you wish to
use an alternative more suited for production.

## How do you deploy it?

Using the Kubeflow Metadata Store in your stack assumes that you already have
a [Kubeflow Orchestrator](../orchestrators/kubeflow.md) included in the same
stack. With that prerequisite in check, configuring the Kubeflow Metadata Store
is pretty straightforward, e.g.:

```shell
# Register the Kubeflow orchestrator
zenml orchestrator register kubeflow_orchestrator --flavor=kubeflow \
    --kubernetes_context=<kubernetes_context>

# Register the Kubeflow metadata store
zenml metadata-store register kubeflow_metadata_store \
    --flavor=kubeflow
    
# Register and set a stack with the new metadata store and orchestrator
zenml stack register kubeflow_stack -m kubeflow_metadata_store \
    -o kubeflow_metadata_store ... --set

# Run `zenml stack up` to forward the metadata store port locally
zenml stack up
```

The `zenml stack up` command must be run locally to forward the metadata store
port locally.

For more, up-to-date information on the Kubeflow Metadata Store implementation
and its configuration, you can have a look at [the API docs](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubeflow.metadata_stores.kubeflow_metadata_store).


## How do you use it?

Aside from the fact that the metadata information is stored using a Kubeflow
ML metadata service, using the Kubeflow Metadata Store is no different than [using any other flavor of Metadata Store](./overview.md#how-to-use-it).

You can also check out our examples pages for working examples that use the
Kubeflow Metadata Store in their stacks:

- [Pipeline Orchestration with Kubeflow](https://github.com/zenml-io/zenml/tree/main/examples/kubeflow_pipelines_orchestration)