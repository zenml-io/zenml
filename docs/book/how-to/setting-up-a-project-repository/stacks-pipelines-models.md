# Organizing Stacks, Pipelines, and Models

In ZenML, pipelines, stacks and models form a crucial part of your project's
architecture and how you choose to use them dictates how well organized your
code and workflow is. This section will give you an overview of how to think
about these concepts and how to best utilize them.

Before we begin, here is a quick overview of the concepts we will be discussing:

- **Stacks**: [Stacks](../../user-guide/production-guide/understand-stacks.md) represent the configuration of tools and infrastructure that your pipelines can run on. A stack is built of multiple stack components like an orchestrator, a container registry, an artifact store, etc. Each of these components deal with one part of your workflow and work together to run your pipeline.
- **Pipelines**: [Pipelines](../../user-guide/starter-guide/create-an-ml-pipeline.md) are a series of steps that each represent a specific task in your ML workflow and are executed in a sequence that ZenML determines from your pipeline definition. Pipelines help you automate many tasks, standardize your executions, and add visibility into what your code is doing.
- **Models**: [Models](../../how-to/use-the-model-control-plane/README.md) are entities that groups pipelines, artifacts, metadata, and other crucial business data together. You may think of a ZenML Model as a "project" or a "workspace" that spans multiple pipelines.

Understanding the relationships between stacks, pipelines, and models is crucial for effective MLOps with ZenML.

## How many Stacks do I need?

A stack provides the infrastructure and tools for running pipelines. Think of a stack as a  representation of your execution environment in which your pipelines are run. This comprises both the hardware like the orchestration environment and any MLOps tools you use in your workflow. This way, Stacks allow you to seamlessly transition between different environments (e.g., local, staging, production) while keeping your pipeline code consistent.

You can learn more about organizing and managing stacks in the [Managing Stacks and Components](../../how-to/stack-deployment/README.md) guide.

You don't need a separate stack for each pipeline; instead, you can run multiple pipelines on the same stack. A stack is meant to be created once and then reused across multiple users and pipelines. This helps in the following ways:

- reduces the overhead of configuring your infrastructure every time you run a pipeline.
- provides a consistent environment for your pipelines to run in, promoting reproducibility.
- reduces risk of errors when it comes to what hardware and tool configurations to use.

As for Models, they are independent of the stack used to create them. Models in ZenML help you tie resources from multiple pipelines together, as you will learn in the next section.


## How do I organize my Pipelines and Models?

A pipeline typically encompasses the entire ML workflow, including data preparation, model training, and evaluation. It's a good practice to have a separate pipeline for different tasks like training and inference. This makes your pipelines more modular and easier to manage.

- separation of pipelines by the nature of the task allows you to run them independently as needed. For example, you might train a model in a training pipeline only once a week but run inference on new data every day.
- it becomes easier to manage and update your code as your project grows more complex.
- different people can work on the code for the pipelines without interfering with each other.
- it helps you organize your runs better.


Models are what tie related pipelines together. A Model in ZenML is a collection of data artifacts, model artifacts, pipelines and metadata that can all be tied to a specific project.
As such, it is good practice to use a Model to move data between pipelines.

Continuing with the example of a training and an inference pipeline, you can use a ZenML Model to handover the trained model from the training pipeline to the inference pipeline. The Model Control Plane allows you to set Stages for specific model versions that can help with this.




<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


