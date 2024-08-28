---
description: Understand how ZenML stores your data under-the-hood.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# How ZenML stores data

ZenML seamlessly integrates data versioning and lineage into its core functionality. When a pipeline is executed, each run generates automatically tracked and managed artifacts. One can easily view the entire lineage of how artifacts are created and interact with them. The dashboard is also a way to interact with the artifacts produced by different pipeline runs. ZenML's artifact management, caching, lineage tracking, and visualization capabilities can help gain valuable insights, streamline the experimentation process, and ensure the reproducibility and reliability of machine learning workflows.

## Artifact Creation and Caching

Each time a ZenML pipeline runs, the system first checks if there have been any changes in the inputs, outputs, parameters, or configuration of the pipeline steps. Each step in a run gets a new directory in the artifact store:

![Artifact Stores Under the Hood](../../.gitbook/assets/zenml_artifact_store_underthehood_1.png)

Suppose a step is new or has been modified. In that case, ZenML creates a new directory structure in the [Artifact Store](../../component-guide/artifact-stores/artifact-stores.md) with a unique ID and stores the data using the appropriate materializers in this directory.

![Artifact Stores Under the Hood](../../.gitbook/assets/zenml_artifact_store_underthehood_2.png)

On the other hand, if the step remains unchanged, ZenML intelligently decides whether to cache the step or not. By caching steps that have not been modified, ZenML can save [valuable time and computational resources](../../user-guide/starter-guide/cache-previous-executions.md), allowing you to focus on experimenting with different configurations and improving your machine-learning models without the need to rerun unchanged parts of your pipeline.

With ZenML, you can easily trace an artifact back to its origins and understand the exact sequence of executions that led to its creation, such as a trained model. This feature enables you to gain insights into the entire lineage of your artifacts, providing a clear understanding of how your data has been processed and transformed throughout your machine-learning pipelines. With ZenML, you can ensure the reproducibility of your results, and identify potential issues or bottlenecks in your pipelines. This level of transparency and traceability is essential for maintaining the reliability and trustworthiness of machine learning projects, especially when working in a team or across different environments.

For more details on how to adjust the names or versions assigned to your artifacts, assign tags to them, or adjust other artifact properties, see the [documentation on artifact versioning and configuration](../../user-guide/starter-guide/manage-artifacts.md).

By tracking the lineage of artifacts across environments and stacks, ZenML enables ML engineers to reproduce results and understand the exact steps taken to create a model. This is crucial for ensuring the reliability and reproducibility of machine learning models, especially when working in a team or across different environments.

## Saving and Loading Artifacts with Materializers

[Materializers](handle-custom-data-types.md) play a crucial role in ZenML's artifact management system. They are responsible for handling the serialization and deserialization of artifacts, ensuring that data is consistently stored and retrieved from the [artifact store](../../component-guide/artifact-stores/artifact-stores.md). Each materializer stores data flowing through a pipeline in one or more files within a unique directory in the artifact store:

![Visualizing artifacts](../../.gitbook/assets/zenml_artifact_store_underthehood_3.png)

Materializers are designed to be extensible and customizable, allowing you to define your own serialization and deserialization logic for specific data types or storage systems. By default, ZenML provides built-in materializers for common data types and uses `cloudpickle` to pickle objects where there is no default materializer. If you want direct control over how objects are serialized, you can easily create custom materializers by extending the `BaseMaterializer` class and implementing the required methods for your specific use case. Read more about materializers [here](handle-custom-data-types.md).

{% hint style="warning" %}
ZenML provides a built-in [CloudpickleMaterializer](https://sdkdocs.zenml.io/latest/core\_code\_docs/core-materializers/#zenml.materializers.cloudpickle\_materializer.CloudpickleMaterializer) that can handle any object by saving it with [cloudpickle](https://github.com/cloudpipe/cloudpickle). However, this is not production-ready because the resulting artifacts cannot be loaded when running with a different Python version. In such cases, you should consider building a [custom Materializer](handle-custom-data-types.md#custom-materializers) to save your objects in a more robust and efficient format.

Moreover, using the `CloudpickleMaterializer` could allow users to upload of any kind of object. This could be exploited to upload a malicious file, which could execute arbitrary code on the vulnerable system.
{% endhint %}

When a pipeline runs, ZenML uses the appropriate materializers to save and load artifacts using the ZenML `fileio` system (built to work across multiple artifact stores). This not only simplifies the process of working with different data formats and storage systems but also enables artifact caching and lineage tracking. You can see an example of a default materializer (the `numpy` materializer) in action [here](https://github.com/zenml-io/zenml/blob/main/src/zenml/materializers/numpy\_materializer.py).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
