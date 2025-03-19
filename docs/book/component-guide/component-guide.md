---
description: Overview of categories of MLOps components and third-party integrations.
icon: scroll
---

# Overview

If you are new to the world of MLOps, it is often daunting to be immediately faced with a sea of tools that seemingly all promise and do the same things. It is useful in this case to try to categorize tools in various groups in order to understand their value in your toolchain in a more precise manner.

ZenML tackles this problem by introducing the concept of [Stacks and Stack Components](https://docs.zenml.io/user-guides/production-guide/understand-stacks). These stack components represent categories, each of which has a particular function in your MLOps pipeline. ZenML realizes these stack components as base abstractions that standardize the entire workflow for your team. In order to then realize the benefit, one can write a concrete implementation of the [abstraction](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component), or use one of the many built-in integrations that implement these abstractions for you.

Here is a full list of all stack components currently supported in ZenML, with a description of the role of that component in the MLOps process:

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-cover data-type="files"></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Orchestrator</strong></td><td>Orchestrating the runs of your pipeline</td><td><a href=".gitbook/assets/orchestrator.png">orchestrator.png</a></td><td><a href="orchestrators/">orchestrators</a></td></tr><tr><td><strong>Artifact Store</strong></td><td>Storage for the artifacts created by your pipelines</td><td><a href=".gitbook/assets/artifact-store.png">artifact-store.png</a></td><td><a href="artifact-stores/">artifact-stores</a></td></tr><tr><td><strong>Container Registry</strong></td><td>Store for your containers</td><td><a href=".gitbook/assets/container-registry.png">container-registry.png</a></td><td><a href="container-registries/">container-registries</a></td></tr><tr><td><strong>Data Validator</strong></td><td>Data and model validation</td><td><a href=".gitbook/assets/data-validator.png">data-validator.png</a></td><td><a href="data-validators/">data-validators</a></td></tr><tr><td><strong>Experiment Tracker</strong></td><td>Tracking your ML experiments</td><td><a href=".gitbook/assets/experiment-tracker.png">experiment-tracker.png</a></td><td><a href="experiment-trackers/">experiment-trackers</a></td></tr><tr><td><strong>Model Deployer</strong></td><td>Services/platforms responsible for online model serving</td><td><a href=".gitbook/assets/model-deployer.png">model-deployer.png</a></td><td><a href="model-deployers/">model-deployers</a></td></tr><tr><td><strong>Step Operator</strong></td><td>Execution of individual steps in specialized runtime environments</td><td><a href=".gitbook/assets/step-operator.png">step-operator.png</a></td><td><a href="step-operators/">step-operators</a></td></tr><tr><td><strong>Alerter</strong></td><td>Sending alerts through specified channels</td><td><a href=".gitbook/assets/alerter.png">alerter.png</a></td><td><a href="alerters/">alerters</a></td></tr><tr><td><strong>Image Builder</strong></td><td>Builds container images.</td><td><a href=".gitbook/assets/image-builder.png">image-builder.png</a></td><td><a href="image-builders/">image-builders</a></td></tr><tr><td><strong>Annotator</strong></td><td>Labeling and annotating data</td><td><a href=".gitbook/assets/annotator.png">annotator.png</a></td><td><a href="annotators/">annotators</a></td></tr><tr><td><strong>Model Registry</strong></td><td>Manage and interact with ML Models</td><td><a href=".gitbook/assets/model-registry.png">model-registry.png</a></td><td><a href="model-registries/">model-registries</a></td></tr><tr><td><strong>Feature Store</strong></td><td>Management of your data/features</td><td><a href=".gitbook/assets/feature-store.png">feature-store.png</a></td><td><a href="feature-stores/">feature-stores</a></td></tr></tbody></table>

Each pipeline run that you execute with ZenML will require a **stack** and each **stack** will be required to include at least an orchestrator and an artifact store. Apart from these two, the other components are optional and to be added as your pipeline evolves in MLOps maturity.

## Writing custom component flavors

You can take control of how ZenML behaves by creating your own components. This is done by writing custom component `flavors`. To learn more, head over to [the general guide on writing component flavors](https://docs.zenml.io/how-to/infrastructure-deployment/stack-deployment/implement-a-custom-stack-component), or read more specialized guides for specific component types (e.g. the [custom orchestrator guide](orchestrators/custom.md)).

## Integrations

Categorizing the MLOps stack is a good way to write abstractions for an MLOps pipeline and standardize your processes. But ZenML goes further and also provides concrete implementations of these categories by **integrating** with various tools for each category. Once code is organized into a ZenML pipeline, you can supercharge your ML workflows with the best-in-class solutions from various MLOps areas.

For example, you can orchestrate your ML pipeline workflows using [Airflow](orchestrators/airflow.md) or [Kubeflow](orchestrators/kubeflow.md), track experiments using [MLflow Tracking](experiment-trackers/mlflow.md) or [Weights & Biases](experiment-trackers/wandb.md), and transition seamlessly from a local [MLflow deployment](model-deployers/mlflow.md) to a deployed model on Kubernetes using [Seldon Core](model-deployers/seldon.md).

There are lots of moving parts for all the MLOps tooling and infrastructure you require for ML in production and ZenML brings them all together and enables you to manage them in one place. This also allows you to delay the decision of which MLOps tool to use in your stack as you have no vendor lock-in with ZenML and can easily switch out tools as soon as your requirements change.

![ZenML is the glue](../.gitbook/assets/zenml-is-the-glue.jpeg)

### Available integrations

We have a [dedicated webpage](https://zenml.io/integrations) that indexes all supported ZenML integrations and their categories.

Another easy way of seeing a list of integrations is to see the list of directories in the [integrations directory](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations) on our GitHub.

### Installing ZenML integrations

Before you can use integrations, you first need to install them using `zenml integration install`, e.g., you can install [Kubeflow](orchestrators/kubeflow.md), [MLflow Tracking](experiment-trackers/mlflow.md), and [Seldon Core](model-deployers/seldon.md), using:

```
zenml integration install kubeflow mlflow seldon -y
```

Under the hood, this simply installs the preferred versions of all integrations using pip, i.e., it executes in a sub-process call:

```
pip install kubeflow==<PREFERRED_VERSION> mlflow==<PREFERRED_VERSION> seldon==<PREFERRED_VERSION>
```

{% hint style="info" %}
* The `-y` flag confirms all `pip install` commands without asking you for

You can run `zenml integration --help` to see a full list of CLI commands that ZenML provides for interacting with integrations.
{% endhint %}

Note, that you can also install your dependencies directly, but please note that there is no guarantee that ZenML internals with work with any arbitrary version of any external library.

#### Use `uv` for package installation

You can use [`uv`](https://github.com/astral-sh/uv) as a package manager if you want. Simply pass the `--uv` flag to the `zenml integration ...` command and it'll use `uv` for installation, upgrades and uninstalls. Note that `uv` must be installed for this to work. This is an experimental option that we've added for users wishing to use `uv` but given that it is relatively new as an option there might be certain packages that don't work well with `uv`.

Full documentation for how it works with PyTorch can be found on Astral's docs website [here](https://docs.astral.sh/uv/guides/integration/pytorch/). It covers some of the particular gotchas and details you might need to know.

### Upgrade ZenML integrations

You can upgrade all integrations to their latest possible version using:

```bash
zenml integration upgrade mlflow pytorch -y
```

{% hint style="info" %}
* The `-y` flag confirms all `pip install --upgrade` commands without asking you for confirmation.
* If no integrations are specified, all installed integrations will be upgraded.
{% endhint %}

### Help us with integrations!

There are countless tools in the ML / MLOps field. We have made an initial prioritization of which tools to support with integrations that are visible on our public [roadmap](https://zenml.io/roadmap).

We also welcome community contributions. Check our [Contribution Guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) and [External Integration Guide](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/README.md) for more details on how to best contribute to new integrations.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
