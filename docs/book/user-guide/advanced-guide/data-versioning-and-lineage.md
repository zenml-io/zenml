---
description: How data is managed in ZenML.
---

# TODO 

- Put these in the right order and explain how the dirs are made
![Visualizing artifacts](../../.gitbook/assets/zenml_artifact_store_underthehood_1.png)

![Visualizing artifacts](../../.gitbook/assets/zenml_artifact_store_underthehood_2.png)

![Visualizing artifacts](../../.gitbook/assets/zenml_artifact_store_underthehood_3.png)

# ENDTODO

# Data versioning and artifact management in ZenML

In this guide, we will explore how ZenML seamlessly integrates data versioning and lineage into its core functionality. When you create and execute ZenML pipelines, each run generates artifacts that are automatically tracked and managed by ZenML. This allows you to easily view the entire lineage of how artifacts are created and interact with them through the [post-execution workflow](../starter-guide/fetch-runs-after-execution.md). ZenML's artifact management, caching, lineage tracking, and visualization capabilities can help you gain valuable insights, streamline your experimentation process, and ensure the reproducibility and reliability of your machine learning workflows.

## Artifact Management with Materializers

Materializers play a crucial role in ZenML's artifact management system. They are responsible for handling the serialization and deserialization of artifacts, ensuring that data is consistently stored and retrieved from the Artifact Store. This allows ZenML to maintain a uniform way of managing artifacts across different data types and storage systems, making it easier for you to work with various data formats and storage solutions in your ML pipelines. Materializers are designed to be extensible and customizable, allowing you to define your own serialization and deserialization logic for specific data types or storage systems. By default, ZenML provides built-in materializers for common data types such as NumPy arrays, Pandas DataFrames, and TensorFlow models. However, you can easily create your own custom materializers by extending the `BaseMaterializer` class and implementing the required methods for your specific use case. Read more about materializers [here](handle-custom-data-types.md).

When a pipeline runs, ZenML uses the appropriate materializers to save and load artifacts, ensuring that the data is consistently managed throughout the pipeline execution. This not only simplifies the process of working with different data formats and storage systems but also enables artifact caching and lineage tracking, which are essential for efficient experimentation and reproducibility in machine learning workflows.

## Artifact Versioning, Caching, and Lineage

Each time a ZenML pipeline runs, the system first checks if there have been any changes in the inputs, outputs, parameters, or configuration of the pipeline steps. If a step is new or has been modified, ZenML creates a new directory structure in the Artifact Store with a unique ID and stores the data using the appropriate materializers in this directory.

On the other hand, if the step remains unchanged, ZenML intelligently decides whether to cache the step or not. By caching steps that have not been modified, ZenML can save valuable time and computational resources, allowing you to focus on experimenting with different configurations and improving your machine learning models without the need to rerun unchanged parts of your pipeline. This efficient caching mechanism is a key feature of ZenML's artifact management system, contributing to the overall performance and flexibility of your machine learning workflows.

With ZenML's [post-execution workflow](../starter-guide/fetch-runs-after-execution.md), you can easily trace an artifact back to its origins and understand the exact sequence of executions that led to its creation, such as a trained model. This powerful feature enables you to gain insights into the entire lineage of your artifacts, providing a clear understanding of how your data has been processed and transformed throughout your machine learning pipelines. By leveraging the post-execution workflow, you can ensure the reproducibility of your results, identify potential issues or bottlenecks in your pipelines, and make informed decisions to optimize your machine learning models and workflows. This level of transparency and traceability is essential for maintaining the reliability and trustworthiness of your machine learning projects, especially when working in a team or across different environments.

By tracking the lineage of artifacts across environments and stacks, ZenML enables ML engineers to reproduce results and understand the exact steps taken to create a model. This is crucial for ensuring the reliability and reproducibility of machine learning models, especially when working in a team or across different environments.

## Visualizing Artifacts

![Visualizing artifacts](../../.gitbook/assets/intro_dashboard_details.png)

In addition to handling the storage and retrieval of artifacts, materializers can also be used to generate visualizations for your data. By overriding the `save_visualizations()` method in your custom materializer, you can create tailored visualizations for your specific artifact types. These visualizations can then be viewed in the ZenML dashboard or interactively explored in Jupyter notebooks using the `visualize()` method of an artifact.

ZenML automatically saves visualizations for many common data types, allowing you to view these visualizations in the ZenML dashboard. This provides an intuitive way to explore and understand the artifacts generated by your ML pipelines, making it easier to identify patterns, trends, and potential issues in your data and models.

In addition to the dashboard, you can also view visualizations in Jupyter notebooks using the `visualize()` method of an artifact. This allows you to interactively explore your artifacts and their visualizations within your notebook environment.

By leveraging ZenML's artifact management, caching, lineage tracking, and visualization capabilities, ML engineers can gain valuable insights into their models, streamline their experimentation process, and ensure the reproducibility and reliability of their machine learning workflows.