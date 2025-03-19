---
description: Storing artifacts on your local filesystem.
---

# Local Artifact Store

The local Artifact Store is a built-in ZenML [Artifact Store](./) flavor that uses a folder on your local filesystem to store artifacts.

### When would you want to use it?

The local Artifact Store is a great way to get started with ZenML, as it doesn't require you to provision additional local resources or to interact with managed object-store services like Amazon S3 and Google Cloud Storage. All you need is the local filesystem. You should use the local Artifact Store if you're just evaluating or getting started with ZenML, or if you are still in the experimental phase and don't need to share your pipeline artifacts (dataset, models, etc.) with others.

{% hint style="warning" %}
The local Artifact Store is not meant to be utilized in production. The local filesystem cannot be shared across your team and the artifacts stored in it cannot be accessed from other machines. This also means that [artifact visualizations](https://docs.zenml.io/how-to/data-artifact-management/visualize-artifacts/) will not be available when using a local Artifact Store through a [ZenML instance deployed in the cloud](https://docs.zenml.io/getting-started/deploying-zenml/).

Furthermore, the local Artifact Store doesn't cover services like high-availability, scalability, backup and restore and other features that are expected from a production grade MLOps system.

The fact that it stores artifacts on your local filesystem also means that not all stack components can be used in the same stack as a local Artifact Store:

* only [Orchestrators](https://docs.zenml.io/stacks/orchestrators/) running on the local machine, such as the [local Orchestrator](https://docs.zenml.io/stacks/orchestrators/local), a [local Kubeflow Orchestrator](https://docs.zenml.io/stacks/orchestrators/kubeflow), or a [local Kubernetes Orchestrator](https://docs.zenml.io/stacks/orchestrators/kubernetes) can be combined with a local Artifact Store
* only [Model Deployers](https://docs.zenml.io/stacks/model-deployers/) that are running locally, such as the [MLflow Model Deployer](https://docs.zenml.io/stacks/model-deployers/mlflow), can be used in combination with a local Artifact Store
* [Step Operators](https://docs.zenml.io/stacks/step-operators/): none of the Step Operators can be used in the same stack as a local Artifact Store, given that their very purpose is to run ZenML steps in remote specialized environments

As you transition to a team setting or a production setting, you can replace the local Artifact Store in your stack with one of the other flavors that are better suited for these purposes, with no changes required in your code.
{% endhint %}

### How do you deploy it?

The `default` stack that comes pre-configured with ZenML already contains a local Artifact Store:

```
$ zenml stack list
Running without an active repository root.
Using the default local database.
┏━━━━━━━━┯━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━┓
┃ ACTIVE │ STACK NAME │ ARTIFACT_STORE │ ORCHESTRATOR ┃
┠────────┼────────────┼────────────────┼──────────────┨
┃   👉   │ default    │ default        │ default      ┃
┗━━━━━━━━┷━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━┛

$ zenml artifact-store describe
Running without an active repository root.
Using the default local database.
Running with active stack: 'default'
No component name given; using `default` from active stack.
                           ARTIFACT_STORE Component Configuration (ACTIVE)                           
┏━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ COMPONENT_PROPERTY │ VALUE                                                                        ┃
┠────────────────────┼──────────────────────────────────────────────────────────────────────────────┨
┃ TYPE               │ artifact_store                                                               ┃
┠────────────────────┼──────────────────────────────────────────────────────────────────────────────┨
┃ FLAVOR             │ local                                                                        ┃
┠────────────────────┼──────────────────────────────────────────────────────────────────────────────┨
┃ NAME               │ default                                                                      ┃
┠────────────────────┼──────────────────────────────────────────────────────────────────────────────┨
┃ UUID               │ 2b7773eb-d371-4f24-96f1-fad15e74fd6e                                         ┃
┠────────────────────┼──────────────────────────────────────────────────────────────────────────────┨
┃ PATH               │ /home/stefan/.config/zenml/local_stores/2b7773eb-d371-4f24-96f1-fad15e74fd6e ┃
┗━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

As shown by the `PATH` value in the `zenml artifact-store describe` output, the artifacts are stored inside a folder on your local filesystem.

You can create additional instances of local Artifact Stores and use them in your stacks as you see fit, e.g.:

```shell
# Register the local artifact store
zenml artifact-store register custom_local --flavor local

# Register and set a stack with the new artifact store
zenml stack register custom_stack -o default -a custom_local --set
```

{% hint style="warning" %}
Same as all other Artifact Store flavors, the local Artifact Store does take in a `path` configuration parameter that can be set during registration to point to a custom path on your machine. However, it is highly recommended that you rely on the default `path` value, otherwise, it may lead to unexpected results. Other local stack components depend on the convention used for the default path to be able to access the local Artifact Store.
{% endhint %}

For more, up-to-date information on the local Artifact Store implementation and its configuration, you can have a look at [the SDK docs](https://sdkdocs.zenml.io/latest/core_code_docs/core-artifact_stores.html#zenml.artifact_stores.local_artifact_store) .

### How do you use it?

Aside from the fact that the artifacts are stored locally, using the local Artifact Store is no different from [using any other flavor of Artifact Store](./#how-to-use-it).

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
