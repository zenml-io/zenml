# Organizing Stacks, Pipelines, Models, and Artifacts

In ZenML, pipelines, stacks and models form a crucial part of your project's
architecture and how you choose to use them dictates how well organized your
code and workflow is. This section will give you an overview of how to think
about these concepts and how to best utilize them.

Before we begin, here is a quick overview of the concepts we will be discussing:

- **Stacks**: [Stacks](../../user-guide/production-guide/understand-stacks.md) represent the configuration of tools and infrastructure that your pipelines can run on. A stack is built of multiple stack components like an orchestrator, a container registry, an artifact store, etc. Each of these components deal with one part of your workflow and work together to run your pipeline.
- **Pipelines**: [Pipelines](../../user-guide/starter-guide/create-an-ml-pipeline.md) are a series of steps that each represent a specific task in your ML workflow and are executed in a sequence that ZenML determines from your pipeline definition. Pipelines help you automate many tasks, standarize your executions, and add visibility into what your code is doing.
- **Models**: [Models](../../how-to/use-the-model-control-plane/README.md) are entities that groups pipelines, artifacts, metadata, and other crucial business data together. You may think of a ZenML Model as a "project" or a "workspace" that spans multiple pipelines.
- **Artifacts**: [Artifacts](../../user-guide/starter-guide/manage-artifacts.md) are the output of a pipeline step that you want to track and reuse across multiple pipelines.

Understanding the relationships between stacks, pipelines, models, and artifacts is crucial for effective MLOps with ZenML.

## How many Stacks do I need?

A stack provides the infrastructure and tools for running pipelines. Think of a stack as a  representation of your execution environment in which your pipelines are run. This comprises both the hardware like the orchestration environment and any MLOps tools you use in your workflow. This way, Stacks allow you to seamlessly transition between different environments (e.g., local, staging, production) while keeping your pipeline code consistent.

You can learn more about organizing and managing stacks in the [Managing Stacks and Components](../../how-to/stack-deployment/README.md) guide.

You don't need a separate stack for each pipeline; instead, you can run multiple pipelines on the same stack. A stack is meant to be created once and then reused across multiple users and pipelines. This helps in the following ways:

- reduces the overhead of configuring your infrastructure every time you run a pipeline.
- provides a consistent environment for your pipelines to run in, promoting reproducibility.
- reduces risk of errors when it comes to what hardware and tool configurations to use.

As for Models, they are independent of the stack used to create them. Models in ZenML help you tie resources from multiple pipelines together, as you will learn in the next section.


## How do I organize my Pipelines, Models, and Artifacts?

Pipelines, Models, and Artifacts form the core of your ML workflow in ZenML. All of your project logic is organized around these concepts and as such, it helps to understand how they interact with each other and how to structure your code to make the most out of them.

### Pipelines

A pipeline typically encompasses the entire ML workflow, including data preparation, model training, and evaluation. It's a good practice to have a separate pipeline for different tasks like training and inference. This makes your pipelines more modular and easier to manage.

- separation of pipelines by the nature of the task allows you to run them independently as needed. For example, you might train a model in a training pipeline only once a week but run inference on new data every day.
- it becomes easier to manage and update your code as your project grows more complex.
- different people can work on the code for the pipelines without interfering with each other.
- it helps you organize your runs better.

### Models

Models are what tie related pipelines together. A Model in ZenML is a collection of data artifacts, model artifacts, pipelines and metadata that can all be tied to a specific project.
As such, it is good practice to use a Model to move data between pipelines.

Continuing with the example of a training and an inference pipeline, you can use a ZenML Model to handover the trained model from the training pipeline to the inference pipeline. The Model Control Plane allows you to set Stages for specific model versions that can help with this.

### Artifacts

Artifacts are the output of a pipeline step that you want to track and reuse across multiple pipelines. They can be anything from a dataset to a trained model. It is a good practice to name your artifacts appropriately to make them easy to identify and reuse. Every pipeline run that results in a unique execution of a pipeline step produces a new version of your artifact. This ensures that there's a clear history and traceability of your data and model artifacts.

Artifacts can be tied to a Model for better organization and visibility across pipelines. You can choose to log metadata about your artifacts which will then show up in the Model Control Plane.

## So how do I put this all together?

Let's go through a real-world example to see how we can use Stacks, Pipelines, Models, and Artifacts together. Imagine there are two people in your team working on a classification model, Bob and Alice.

Here's how the workflow would look like with ZenML:
- They create three pipelines: one for feature engineering, one for training the model, and one for producing predictions.
- They set up a [repository for their project](../setting-up-a-project-repository/README.md) and start building their pipelines collaboratively. Let's assume Bob builds the feature engineering and training pipeline and Alice builds the inference pipeline.
- To test their pipelines locally, they both have a `default` stack with a local orchestrator and a local artifact store. This allows them to quickly iterate on their code without deploying any infrastructure or incurring any costs.
- While building the inference pipeline, Alice needs to make sure that the preprocessing step in her pipeline is the same as the one used while training. It might even involve the use of libraries that are not publicily available and she follows the [Shared Libraries and Logic for Teams](./shared_components_for_teams.md) guide to help with this.
- Bob's training pipeline produces a model artifact, which Alice's inference pipeline requires as input. It also produces other artifacts such as metrics and a model checkpoint that are logged as artifacts in the pipeline run.
- To allow easy access to model and data artifacts, they [use a ZenML Model](../../how-to/use-the-model-control-plane/associate-a-pipeline-with-a-model.md) which ties the pipelines, models and artifacts together. Now Alice can just [refernce the right model name and find the model artifact she needs](../../how-to/use-the-model-control-plane/load-artifacts-from-model.md).
- It is also critical that the right model version from the training pipeline is used in the inference pipeline. The [Model Control Plane](../../how-to/use-the-model-control-plane/README.md) helps Bob to keep track of the different versions and to easily compare them. Bob can then [promote the best performing model version to the `production` stage](../../how-to/use-the-model-control-plane/promote-a-model.md) which Alice's pipeline can then consume.
- Alice's inference pipeline produces a new artifact, in this case a new dataset containing the predictions of the model. Results can also be added as metadata to the model version, allowing easy comparisons.

This is a very simple example, but it shows how you can use ZenML to structure your ML workflow. You can use the same principles for more complex workflows. 



<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>


