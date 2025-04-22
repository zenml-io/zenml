---
icon: box-archive
---

# Integrations

Categorizing the MLOps stack is a good way to write abstractions for an MLOps pipeline and standardize your processes. But ZenML goes further and also provides concrete implementations of these categories by **integrating** with various tools for each category. Once code is organized into a ZenML pipeline, you can supercharge your ML workflows with the best-in-class solutions from various MLOps areas.

For example, you can orchestrate your ML pipeline workflows using [Airflow](orchestrators/airflow.md) or [Kubeflow](orchestrators/kubeflow.md), track experiments using [MLflow Tracking](experiment-trackers/mlflow.md) or [Weights & Biases](experiment-trackers/wandb.md), and transition seamlessly from a local [MLflow deployment](model-deployers/mlflow.md) to a deployed model on Kubernetes using [Seldon Core](model-deployers/seldon.md).

There are lots of moving parts for all the MLOps tooling and infrastructure you require for ML in production and ZenML brings them all together and enables you to manage them in one place. This also allows you to delay the decision of which MLOps tool to use in your stack as you have no vendor lock-in with ZenML and can easily switch out tools as soon as your requirements change.

![ZenML is the glue](../.gitbook/assets/zenml-is-the-glue.jpeg)

## Available integrations

We have a [dedicated webpage](https://zenml.io/integrations) that indexes all supported ZenML integrations and their categories.

Another easy way of seeing a list of integrations is to see the list of directories in the [integrations directory](https://github.com/zenml-io/zenml/tree/main/src/zenml/integrations) on our GitHub.

## Installing dependencies for integrations and stacks

ZenML provides a way to export the package requirements for both individual integrations and entire stacks, enabling you to install the necessary dependencies manually. This approach gives you full control over the versions and the installation process.

### Exporting integration requirements

You can export the requirements for a specific integration using the `zenml integration export-requirements` command. To write the requirements to a file and install them via pip, run:

```bash
zenml integration export-requirements <INTEGRATION_NAME> --output-file integration_requirements.txt
pip install -r integration_requirements.txt
```

If you prefer to see the requirements without writing them to a file, omit the `--output-file` flag:

```bash
zenml integration export-requirements <INTEGRATION_NAME>
```

This will print the list of dependencies to the console, which you can then pipe to pip:

```bash
zenml integration export-requirements <INTEGRATION_NAME> | xargs pip install
```

### Exporting stack requirements

To install all dependencies for a specific ZenML stack at once, you can export your stack's requirements:

```bash
zenml stack export-requirements <STACK_NAME> --output-file stack_requirements.txt
pip install -r stack_requirements.txt
```

Omitting `--output-file` will print the requirements to the console:

```bash
zenml stack export-requirements <STACK_NAME>
```

You can also pipe the output directly to pip:

```bash
zenml stack export-requirements <STACK_NAME> | xargs pip install
```

{% hint style="info" %}
If you use a different package manager such as [`uv`](https://github.com/astral-sh/uv), you can install the exported requirements by replacing `pip install -r …` with your package manager's equivalent command.
{% endhint %}

## Help us with integrations!

There are countless tools in the ML / MLOps field. We have made an initial prioritization of which tools to support with integrations that are visible on our public [roadmap](https://zenml.io/roadmap).

We also welcome community contributions. Check our [Contribution Guide](https://github.com/zenml-io/zenml/blob/main/CONTRIBUTING.md) and [External Integration Guide](https://github.com/zenml-io/zenml/blob/main/src/zenml/integrations/README.md) for more details on how to best contribute to new integrations.
