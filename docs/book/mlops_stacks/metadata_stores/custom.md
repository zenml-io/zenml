---
description: Extend ZenML to implement a custom Metadata Store
---

{% hint style="warning" %}
**Base abstraction in progress!**

We are actively working on the base abstraction for the Metadata Stores, which 
will be available soon. As a result, their extension is not recommended at the 
moment. When you are selecting a metadata store for your stack, you can use 
one of [the existing flavors](./overview.md#metadata-store-flavors).

If you need to implement your own Metadata Store flavor, you can still do so,
but keep in mind that you may have to refactor it when the base abstraction
is released. 
{% endhint %}

ZenML comes equipped with [Metadata Store implementations](./overview.md#metadata-store-flavors)
that you can use to store artifacts on a local filesystem, in a MySQL database
or in the metadata service installed with Kubeflow. However, if you need to use
a different type of service as a backend for your ZenML Metadata Store, you can
extend ZenML to provide your own custom Metadata Store implementation.

{% hint style="warning" %}
Before reading this chapter, make sure that you are familiar with the 
concept of [stacks, stack components and their flavors](../advanced-guide/stacks-components-flavors.md).  
{% endhint %}

## Build your own custom metadata store

If you want to implement your own custom Metadata Store, you can follow the
following steps:

1. Create a class which inherits from [the `BaseMetadataStore` class](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.base_metadata_store.BaseMetadataStore).
2. Define the `FLAVOR` class variable.
3. Implement the `abstractmethod`s based on your desired metadata store
connection.

Once you are done with the implementation, you can register it through the CLI 
as:

```shell
zenml metadata-store flavor register <THE-SOURCE-PATH-OF-YOUR-METADATA-STORE>
```

ZenML includes a range of Metadata Store implementations, some built-in and
other provided by specific integration modules. You can use them as examples
of how you can extend the [base Metadata Store class](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.base_metadata_store.BaseMetadataStore)
to implement your own custom Metadata Store:


|                                                                                                                                                                           | Flavor         | Integration  |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|--------------|
| [SQLiteMetadataStore](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.sqlite_metadata_store.SQLiteMetadataStore)                          | sqlite         | `built-in`   |
| [MySQLMetadataStore](https://apidocs.zenml.io/latest/api_docs/metadata_stores/#zenml.metadata_stores.mysql_metadata_store.MySQLMetadataStore)                             | mysql          | `built-in`   |
| [KubeflowMetadataStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubeflow.metadata_stores.kubeflow_metadata_store.KubeflowMetadataStore) | kubeflow       | kubeflow     |
| [KubernetesMetadataStore](https://apidocs.zenml.io/latest/api_docs/integrations/#zenml.integrations.kubernetes.metadata_stores.kubernetes_metadata_store.KubernetesMetadataStore) | kubernetes       | kubernetes     |
