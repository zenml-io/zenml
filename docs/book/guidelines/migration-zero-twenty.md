---
description: Contribute to ZenML!
---

# ZenML 0.13.2 → 0.20.0

This page captures all changes that happened from version 0.13.2 to 0.20.0, which includes the architectural shift towards the server. Please add to this list as you see fit.

As this is a huge breaking change, I would appreciate as much information as possible. I plan to write a blog post that captures the broad strokes, and have a docs page that captures the nitty gritty

- ZenML can now run as a server that can be accessed via REST API and comes with a visual user interface (called the ZenML Dashboard). This server can be deployed in arbitrary environments (local, on-prem, via Docker, on AWS / GCP / Azure / ...) and supports user management, project scoping, and more.
- The new ZenML Dashboard build files are now bundled as part of all future releases, and can be launched directly from within python. The source code lives in the [ZenML Dashboard repository](https://github.com/zenml-io/zenml-ui)
- Metadata Store stack component has been deprecated and is no longer required to create a stack. The role of the Metadata Store is now taken over by the `ZenServer` . All metadata is now stored, tracked, and managed by ZenML itself. To further improve reproducibility, pipelines themselves are now tracked in ZenML (rather than the metadata store) and exposed as first-level citizens. Each pipeline clearly defines what steps are used in the pipeline and in what order the steps are executed. By default, pipeline runs are now scoped by pipeline.
- The KubeflowOrchestrator now no longer supports the KubeflowMetadataStore. Instead, for Kubeflow deployments with ZenML, you must have a deployed ZenML Server, just as you need to have a deployed ZenML server for any remote orchestration system.
- Stack components can now be registered without having the required integrations installed. As part of this change, we split all existing stack component definitions into three classes: An implementation class that defines the logic of the stack component, a config class that defines the attributes and performs input validations, and a flavor class that links implementation and config classes together. See **[component flavor models #895](https://github.com/zenml-io/zenml/pull/895)** for more details.
- There are multiple changes to stack components:
    - enable_whylogs deprecated
    - enable_mlflow deprecated
    - enable_wandb deprecated
- Stacks and Stack Components can be shared through the Zen Server now - to share, either set it as shared during creation time `zenml stack register mystack ... --share`  or afterwards through `zenml stack share mystack`
- Stacks and Stack components can now be addressed by name, id or the first few letters of the id in the cli - for a stack `default` with id `179ebd25-4c5b-480f-a47c-d4f04e0b6185`  you can now do `zenml stack describe default` or `zenml stack describe 179` or `zenml stack describe 179ebd25-4c5b-480f-a47c-d4f04e0b6185`
- `Profiles` have been deprecated as a concept in ZenML. Users no longer have profiles, but instead have to connect to a ZenServer
- `Local YAML ZenStores` have been deprecated.
- The ZenServer story has significant changes:
    - Creating users within a project
- The `Repository` object has been renamed to `Client` to capture its functionality better
- The release introduces a series of commands to manage the lifecycle of the ZenServer
    - `zenml server connect / disconnect / down / up / explain / list / logs / status`
    - `zenml pipeline list / runs / delete`
    - `zenml profile list / migrate`
- With collaboration being the key part of this story, ZenML 0.20.0 introduces the concept of shared stacks
    - default stack is an exception
- We also introduce the notion of `local` vs `non-local` stack components. Local stack components are stack components that are configured to run locally while non-local stack components are configured to run remotely or in a cloud environment. Consequently, stacks made up of local stack components should not be shared on a central ZenML Server.
- Alongside the architectural shift, Pipeline configuration has been completely rethought. ZenML pipelines and steps could previously be configured in many different ways:
    - On the `@pipeline` and `@step` decorators
    - In the `__init__` method of the pipeline and step class
    - Using `@enable_xxx` decorators
    - Using specialized methods like `pipeline.with_config(...)` or `step.with_return_materializer(...)`

Some of the configuration options were quite hidden, difficult to access and not tracked in any way by the ZenML metadata store. The new changes introduced are:

- Pipelines and steps now allow all configurations on their decorators as well as the `.configure(...)` method. This includes configurations for stack components that are not infrastructure-related which was previously done using the `@enable_xxx` decorators)
- The same configurations can also be defined in a yaml file
- The users can think of configuring stacks and pipeline in terms of `Params` and `Settings`
- `BaseStepConfig` is not renamed to `Params`
- `DockerConfiguration` is not `DockerSettings`

- All the aforementioned configurations as well as additional information required to run a ZenML pipelines are now combined into an intermediate representation. Instead of the user-facing `BaseStep` and `BasePipeline` classes, all the ZenML orchestrators and step operators now use this intermediate representation to run pipelines and steps.
- Post-execution workflow has changed as follows:
    - @Alexej Penner or @Baris Can Durak can you help me here?
    - The `get_pipeline` and `get_run` methods have been moved out of the `Repository` (i.e. the new `Client` ) class and lie directly in the post_execution module now. To use the user has to do:
    
    ```bash
    from zenml.post_execution import get_pipeline, get_run
    ```
    
- Once a pipeline has been executed, it is represented by a `PipelineSpec` that uniques identifies it. Therefore, users are no longer able to edit a pipeline once it has been run once. There are now three options to get around this:
    - Pipeline runs can be created without being associated with a pipeline explicitly: We call these `unlisted` runs
    - Pipelines can be deleted and created again
    - Pipelines can be given unique names each time they are run to uniquely identify them
- `zenml config` subgroup has changed

# 👣How to migrate from 0.13.2

@Stefan Nica your guide can be linked here

# 🐞 Reporting Bugs

We should come up with a mechanism to report bugs. Suggestions:

- Open up a Slack Channel
- Open up a GitHub issue in ZenML and ZenML dashboard repositories

# 📡Future Changes

While this rehaul is big and will break previous releases, we do have some more work left to do. We expect this to be the last big rehaul of ZenML before our 1.0.0 release, but no other release will be so hard breaking as this one. Currently planned future breaking changes are:

- Following the metadata store, the secret manager stack component will move out of the stack.
- ZenML `StepContext` might be deprecated

# 💾 The New Way (CLI Command Cheat Sheet)

**deploy the server**

`zenml deploy --aws` (maybe don’t do this :) since it spins up infrastructure on AWS…)

**spin up a local zenserver**

`zenml up`

**connect to a pre-existing server**

`zenml connect` (pass in URL / etc, or zenml connect --config + yaml file)

**List your deployed server details**

`zenml config explain` / `zenml config describe` —