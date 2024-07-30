---
description: Overview of third-party ZenML integrations.
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Integration overview

Categorizing the MLOps stack is a good way to write abstractions for an MLOps pipeline and standardize your processes. But ZenML goes further and also provides concrete implementations of these categories by **integrating** with various tools for each category. Once code is organized into a ZenML pipeline, you can supercharge your ML workflows with the best-in-class solutions from various MLOps areas.

For example, you can orchestrate your ML pipeline workflows using [Airflow](orchestrators/airflow.md) or [Kubeflow](orchestrators/kubeflow.md), track experiments using [MLflow Tracking](experiment-trackers/mlflow.md) or [Weights & Biases](experiment-trackers/wandb.md), and transition seamlessly from a local [MLflow deployment](model-deployers/mlflow.md) to a deployed model on Kubernetes using [Seldon Core](model-deployers/seldon.md).

There are lots of moving parts for all the MLOps tooling and infrastructure you require for ML in production and ZenML brings them all together and enables you to manage them in one place. This also allows you to delay the decision of which MLOps tool to use in your stack as you have no vendor lock-in with ZenML and can easily switch out tools as soon as your requirements change.

![ZenML is the glue](../.gitbook/assets/zenml-is-the-glue.jpeg)

## Available integrations

We have a [dedicated webpage](https://zenml.io/integrations) that indexes all supported ZenML integrations and their categories.

Another easy way of seeing a list of integrations is to see the list of directories in the [integrations directory](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations) on our GitHub.

## Installing ZenML integrations

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

### Experimental: Use `uv` for package installation

You can use [`uv`](https://github.com/astral-sh/uv) as a package manager if you want. Simply pass the `--uv` flag to the `zenml integration ...` command and it'll use `uv` for installation, upgrades and uninstallations. Note that `uv` must be installed for this to work. This is an experimental option that we've added for users wishing to use `uv` but given that it is relatively new as an option there might be certain packages that don't work well with `uv`. We will monitor how this performs and update as `uv` becomes more stable.

## Upgrade ZenML integrations

You can upgrade all integrations to their latest possible version using:

```bash
zenml integration upgrade mlflow pytorch -y
```

{% hint style="info" %}
* The `-y` flag confirms all `pip install --upgrade` commands without asking you for confirmation.
* If no integrations are specified, all installed integrations will be upgraded.
{% endhint %}

## Help us with integrations!

There are countless tools in the ML / MLOps field. We have made an initial prioritization of which tools to support with integrations that are visible on our public [roadmap](https://zenml.io/roadmap).

We also welcome community contributions. Check our [Contribution Guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) and [External Integration Guide](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/README.md) for more details on how to best contribute to new integrations.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
