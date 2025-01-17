---
icon: lightbulb
description: Discovering the core concepts behind ZenML.
---

# Core concepts

![A diagram of core concepts of ZenML OSS](../.gitbook/assets/core_concepts_oss.png)

**ZenML** is an extensible, open-source MLOps framework for creating portable, production-ready **MLOps pipelines**. It's built for data scientists, ML Engineers, and MLOps Developers to collaborate as they develop to production. In order to achieve this goal, ZenML introduces various concepts for different aspects of an ML workflow and we can categorize these concepts under three different threads:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><mark style="color:purple;"><strong>1. Development</strong></mark></td><td>As a developer, how do I design my machine learning workflows?</td><td></td><td><a href="core-concepts.md#1-development">#1-development</a></td></tr><tr><td><mark style="color:purple;"><strong>2. Execution</strong></mark></td><td>While executing, how do my workflows utilize the large landscape of MLOps tooling/infrastructure?</td><td></td><td><a href="core-concepts.md#2-execution">#2-execution</a></td></tr><tr><td><mark style="color:purple;"><strong>3. Management</strong></mark></td><td>How do I establish and maintain a production-grade and efficient solution?</td><td></td><td><a href="core-concepts.md#3-management">#3-management</a></td></tr></tbody></table>

## 1. Development

First, let's look at the main concepts which play a role during the development stage of an ML workflow with ZenML.

#### Step

Steps are functions annotated with the `@step` decorator. The easiest one could look like this.

```python
@step
def step_1() -> str:
    """Returns a string."""
    return "world"
```

These functions can also have inputs and outputs. For ZenML to work properly, these should preferably be typed.

```python
@step(enable_cache=False)
def step_2(input_one: str, input_two: str) -> str:
    """Combines the two strings passed in."""
    combined_str = f"{input_one} {input_two}"
    return combined_str
```

#### Pipelines

At its core, ZenML follows a pipeline-based workflow for your projects. A **pipeline** consists of a series of **steps**, organized in any order that makes sense for your use case.

![Representation of a pipeline dag.](../.gitbook/assets/01\_pipeline.png)

As seen in the image, a step might use the outputs from a previous step and thus must wait until the previous step is completed before starting. This is something you can keep in mind when organizing your steps.

Pipelines and steps are defined in code using Python _decorators_ or _classes_. This is where the core business logic and value of your work lives, and you will spend most of your time defining these two things.

Even though pipelines are simple Python functions, you are only allowed to call steps within this function. The inputs for steps called within a pipeline can either be the outputs of previous steps or alternatively, you can pass in values directly (as long as they're JSON-serializable).

```python
@pipeline
def my_pipeline():
    output_step_one = step_1()
    step_2(input_one="hello", input_two=output_step_one)
```

Executing the Pipeline is as easy as calling the function that you decorated with the `@pipeline` decorator.

```python
if __name__ == "__main__":
    my_pipeline()
```

#### Artifacts

Artifacts represent the data that goes through your steps as inputs and outputs and they are automatically tracked and stored by ZenML in the artifact store. They are produced by and circulated among steps whenever your step returns an object or a value. This means the data is not passed between steps in memory. Rather, when the execution of a step is completed they are written to storage, and when a new step gets executed they are loaded from storage.

The serialization and deserialization logic of artifacts is defined by [Materializers](../how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types.md).

#### Models

Models are used to represent the outputs of a training process along with all metadata associated with that output. In other words: models in ZenML are more broadly defined as the weights as well as any associated information. Models are first-class citizens in ZenML and as such viewing and using them is unified and centralized in the ZenML API, client as well as on the [ZenML Pro](https://zenml.io/pro) dashboard.

#### Materializers

Materializers define how artifacts live in between steps. More precisely, they define how data of a particular type can be serialized/deserialized, so that the steps are able to load the input data and store the output data.

All materializers use the base abstraction called the `BaseMaterializer` class. While ZenML comes built-in with various implementations of materializers for different datatypes, if you are using a library or a tool that doesn't work with our built-in options, you can write [your own custom materializer](../how-to/data-artifact-management/handle-data-artifacts/handle-custom-data-types.md) to ensure that your data can be passed from step to step.

#### Parameters & Settings

When we think about steps as functions, we know they receive input in the form of artifacts. We also know that they produce output (in the form of artifacts, stored in the artifact store). But steps also take parameters. The parameters that you pass into the steps are also (helpfully!) stored by ZenML. This helps freeze the iterations of your experimentation workflow in time, so you can return to them exactly as you run them. On top of the parameters that you provide for your steps, you can also use different `Setting`s to configure runtime configurations for your infrastructure and pipelines.

#### Model and model versions

ZenML exposes the concept of a `Model`, which consists of multiple different model versions. A model version represents a unified view of the ML models that are created, tracked, and managed as part of a ZenML project. Model versions link all other entities to a centralized view.

## 2. Execution

Once you have implemented your workflow by using the concepts described above, you can focus your attention on the execution of the pipeline run.

#### Stacks & Components

When you want to execute a pipeline run with ZenML, **Stacks** come into play. A **Stack** is a collection of **stack components**, where each component represents the respective configuration regarding a particular function in your MLOps pipeline such as orchestration systems, artifact repositories, and model deployment platforms.

For instance, if you take a close look at the default local stack of ZenML, you will see two components that are **required** in every stack in ZenML, namely an _orchestrator_ and an _artifact store_.

![ZenML running code on the Local Stack.](../.gitbook/assets/02\_pipeline\_local\_stack.png)

{% hint style="info" %}
Keep in mind, that each one of these components is built on top of base abstractions and is completely extensible.
{% endhint %}

#### Orchestrator

An **Orchestrator** is a workhorse that coordinates all the steps to run in a pipeline. Since pipelines can be set up with complex combinations of steps with various asynchronous dependencies between them, the orchestrator acts as the component that decides what steps to run and when to run them.

ZenML comes with a default _local orchestrator_ designed to run on your local machine. This is useful, especially during the exploration phase of your project. You don't have to rent a cloud instance just to try out basic things.

#### Artifact Store

An **Artifact Store** is a component that houses all data that pass through the pipeline as inputs and outputs. Each artifact that gets stored in the artifact store is tracked and versioned and this allows for extremely useful features like data caching which speeds up your workflows.

Similar to the orchestrator, ZenML comes with a default _local artifact store_ designed to run on your local machine. This is useful, especially during the exploration phase of your project. You don't have to set up a cloud storage system to try out basic things.

#### Flavor

ZenML provides a dedicated base abstraction for each stack component type. These abstractions are used to develop solutions, called **Flavors**, tailored to specific use cases/tools. With ZenML installed, you get access to a variety of built-in and integrated Flavors for each component type, but users can also leverage the base abstractions to create their own custom flavors.

#### Stack Switching

When it comes to production-grade solutions, it is rarely enough to just run your workflow locally without including any cloud infrastructure.

Thanks to the separation between the pipeline code and the stack in ZenML, you can easily switch your stack independently from your code. For instance, all it would take you to switch from an experimental local stack running on your machine to a remote stack that employs a full-fledged cloud infrastructure is a single CLI command.

## 3. Management

In order to benefit from the aforementioned core concepts to their fullest extent, it is essential to deploy and manage a production-grade environment that interacts with your ZenML installation.

#### ZenML Server

To use _stack components_ that are running remotely on a cloud infrastructure, you need to deploy a [**ZenML Server**](../user-guide/production-guide/deploying-zenml.md) so it can communicate with these stack components and run your pipelines. The server is also responsible for managing ZenML business entities like pipelines, steps, models, etc.

![Visualization of the relationship between code and infrastructure.](../.gitbook/assets/04\_architecture.png)

#### Server Deployment

In order to benefit from the advantages of using a deployed ZenML server, you can either choose to use the [**ZenML Pro SaaS offering**](zenml-pro/README.md) which provides a control plane for you to create managed instances of ZenML servers, or [deploy it in your self-hosted environment](deploying-zenml/README.md).

#### Metadata Tracking

On top of the communication with the stack components, the **ZenML Server** also keeps track of all the bits of metadata around a pipeline run. With a ZenML server, you are able to access all of your previous experiments with the associated details. This is extremely helpful in troubleshooting.

#### Secrets

The **ZenML Server** also acts as a [centralized secrets store](deploying-zenml/secret-management.md) that safely and securely stores sensitive data such as credentials used to access the services that are part of your stack. It can be configured to use a variety of different backends for this purpose, such as the AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, and Hashicorp Vault.

Secrets are sensitive data that you don't want to store in your code or configure alongside your stacks and pipelines. ZenML includes a [centralized secrets store](deploying-zenml/secret-management.md) that you can use to store and access your secrets securely.

#### Collaboration

Collaboration is a crucial aspect of any MLOps team as they often need to bring together individuals with diverse skills and expertise to create a cohesive and effective workflow for machine learning projects. A successful MLOps team requires seamless collaboration between data scientists, engineers, and DevOps professionals to develop, train, deploy, and maintain machine learning models.

With a deployed **ZenML Server**, users have the ability to create their own teams and project structures. They can easily share pipelines, runs, stacks, and other resources, streamlining the workflow and promoting teamwork.

#### Dashboard

The **ZenML Dashboard** also communicates with **the ZenML Server** to visualize your _pipelines_, _stacks_, and _stack components_. The dashboard serves as a visual interface to showcase collaboration with ZenML. You can invite _users_, and share your stacks with them.

When you start working with ZenML, you'll start with a local ZenML setup, and when you want to transition you will need to [deploy ZenML](deploying-zenml/README.md). Don't worry though, there is a one-click way to do it which we'll learn about later.

#### VS Code Extension

ZenML also provides a [VS Code extension](https://marketplace.visualstudio.com/items?itemName=ZenML.zenml-vscode) that allows you to interact with your ZenML stacks, runs and server directly from your VS Code editor. If you're working on code in your editor, you can easily switch and inspect the stacks you're using, delete and inspect pipelines as well as even switch stacks.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
