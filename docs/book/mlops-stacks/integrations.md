---
description: Overview of third-party ZenML integrations
---

{% hint style="warning" %}
This is an older version of the ZenML documentation. To read and view the latest version please [visit this up-to-date URL](https://docs.zenml.io).
{% endhint %}


# Integrating with best-in-breed tools

[Categorizing the MLOps stack](./categories.md) is a good way to write abstractions for 
a MLOps pipeline and standardize your processes. But ZenML goes further and also provides 
concrete implementations of these categories by **integrating** with many different  
tools for each category. Once code is organized into a ZenML pipeline, you can supercharge 
your ML workflows with the best-in-class solutions from various MLOps areas.

In short, an integration in ZenML utilizes a third-party tool to implement 
one or more [Stack Component](../developer-guide/stacks-profiles-repositories/stack.md#stack-components) abstractions.

For example, you can orchestrate your ML pipeline workflows using
[Airflow](./orchestrators/airflow.md) or [Kubeflow](./orchestrators/kubeflow.md),
track experiments using [MLflow Tracking](./experiment-trackers/mlflow.md) or
[Weights & Biases](./experiment-trackers/wandb.md), and transition seamlessly
from a local [MLflow deployment](./model-deployers/mlflow.md) to a deployed model
on Kubernetes using [Seldon Core](./model-deployers/seldon.md).

There are lots of moving parts for all the MLOps tooling and infrastructure you
require for ML in production and ZenML brings them all together and enables you
to manage them in one place. This also allows you to delay the decision of which 
MLOps tool to use in your stack as you have no vendor lock-in with ZenML and 
can easily switch out tools as soon as your requirements change. 

![ZenML is the glue](../assets/zenml-is-the-glue.jpeg)

## Available Integrations

We have a [dedicated webpage](https://zenml.io/integrations) that indexes all supported 
ZenML integrations and their categories.

Another easy way of seeing a list of integrations is to see the list of directories in the 
[integrations directory](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations) 
on our GitHub.

## Installing ZenML Integrations

Before you can use integrations, you first need to install them using 
`zenml integration install`, e.g., you can install
[Kubeflow](./orchestrators/kubeflow.md),
[MLflow Tracking](./experiment-trackers/mlflow.md), 
and [Seldon Core](./model-deployers/seldon.md), using:

```
zenml integration install kubeflow mlflow seldon -y
```

Under the hood, this simply installs the preferred versions of all 
integrations using pip, i.e., it executes in a sub-process call:

```
pip install kubeflow==<PREFERRED_VERSION> mlflow==<PREFERRED_VERSION> seldon==<PREFERRED_VERSION>
```

{% hint style="info" %}
The `-y` flag confirms all `pip install` commands without asking you for
confirmation for every package first. 

You can run `zenml integration --help` to see a full list of CLI commands that
ZenML provides for interacting with integrations.
{% endhint %}

Note, that you can also install your dependencies directly, but please note that 
there is no guarantee that ZenML internals with work with any arbitrary version 
of any external library.

## Help us with integrations!

There are countless tools in the ML / MLOps field. We have made an initial
prioritization of which tools to support with integrations that is visible on 
our public [roadmap](https://zenml.io/roadmap).

We also welcome community contributions. Check our [Contribution Guide](../resources/contributing.md)
and [External Integration Guide](../resources/integrating.md) for more details
on how to best contribute new integrations.
