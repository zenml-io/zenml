# What is a backend?

Production-ready backends when you want to scale

ZenML backends define `how` and `where` ZenML pipelines are run. They are broadly split into three categories:

* [orchestrator](orchestrator-backends.md): Orchestrator backends manage the running of each step of the pipeline
* [processing](processing-backends.md): Processing backends defines the environment in which each step executes its workload
* [training](training-backends.md): Training backends are special and meant only for [Training Pipelines.](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/pipelines/training-pipeline.md) They define the environment in which the training happens

By separating backends from the actual pipeline logic, ZenML achieves a [Terraform](https://www.terraform.io/)-like scalability, [extensibility](https://github.com/maiot-io/zenml/tree/9c7429befb9a99f21f92d13deee005306bd06d66/docs/book/backends/benefits/integrations.md) and reproducibility for all its pipelines. This is achieved whilst also maintaining comparability and consistent evaluation for all pipelines.

Backends too are split into `standard` and `custom` categories. The standard ones can be found at: `zenml.core.backends.*` .

## How to use a backend?

A backend is associated directly with a [pipeline](../pipelines/what-is-a-pipeline.md) and can be specified in different ways using the `backends` argument:

* When constructing a pipeline.
* When executing a `pipeline.run()`.
* When executing a `pipeline.build()`.

## Create your own backend

```text
Before creating your own backend, please make sure to follow the [general rules](../getting-started/creating-custom-logic.md)
for extending any first-class ZenML component.
```

The API to create custom backends is still under active development. Please see this space for updates.

If you would like to see this functionality earlier, please let us know via our [Slack Channel](https://zenml.io/slack-invite/) or [create an issue on GitHub](https://https://github.com/maiot-io/zenml).\)

## What next?

* Set up different [orchestration](orchestrator-backends.md) strategies for your pipelines. Execute pipelines on your local

  machine, to a large instance on the cloud, to a Kubernetes cluster.

* Leverage powerful distributed processing by using built-in [processing](processing-backends.md) backends.
* Train on GPUs in the cloud with various [training](training-backends.md).

