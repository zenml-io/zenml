---
description: Tracking the execution of your pipelines/steps.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To check the latest version please [visit https://docs.zenml.io](https://docs.zenml.io)
{% endhint %}


The configuration of each pipeline, step and produced artifacts are all tracked
within the metadata store. ZenML puts a lot of emphasis on guaranteed tracking 
of inputs across pipeline steps. The strict, fully automated, and deeply 
built-in tracking enables some powerful features - e.g. reproducibility.

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the metadata stores, which 
will be available soon. As a result, their extension is not possible at the 
moment. When you are selecting a metadata store for your stack, you can use 
one of the flavors listed down below.
{% endhint %}

## List of available metadata stores

In its current version, ZenML features three metadata store flavors, namely 
the `sqlite`, `kubeflow`, and `mysql` flavors. These flavors are to be used 
in different contexts, but in general, we suggest to use the `mysql` flavor 
for most use cases.

* `sqlite`: This is the default store. Only use this for running ZenML locally.
* `kubeflow`: Kubeflow boasts an internal metadata store, which ZenML can 
leverage. This flavor of metadata store is only to be used in combination 
with the `KubeflowOrchestrator`.
* `mysql`: To be used for most other production settings, including with 
the `KubeflowOrchestrator` or other orchestrators that do not support an 
internal metadata store.

|                                                                                                                                                                           | Flavor         | Integration  |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|--------------|
| [SQLiteMetadataStore](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.sqlite_metadata_store.SQLiteMetadataStore)                          | sqlite         | `built-in`   |
| [MySQLMetadataStore](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.mysql_metadata_store.MySQLMetadataStore)                             | mysql          | `built-in`   |
| [KubeflowMetadataStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubeflow.metadata_stores.kubeflow_metadata_store.KubeflowMetadataStore) | kubeflow       | kubeflow     |
| [KubernetesMetadataStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubernetes.metadata_stores.kubernetes_metadata_store.KubernetesMetadataStore) | kubernetes       | kubernetes     |

If you would like to see the available flavors for metadata stores, you can 
use the command:

```shell
zenml metadata-store flavor list
```