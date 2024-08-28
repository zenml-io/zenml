---
description: Put your new knowledge into action with a simple starter project
---

# A starter project

By now, you have understood some of the basic pillars of a MLOps system:

* [Pipelines and steps](create-an-ml-pipeline.md)
* [Artifacts](manage-artifacts.md)
* [Models](track-ml-models.md)

We will now put this into action with a simple starter project.

## Get started

Start with a fresh virtual environment with no dependencies. Then let's install our dependencies:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
```

We will then use [ZenML templates](../../how-to/setting-up-a-project-repository/using-project-templates.md) to help us get the code we need for the project:

```bash
mkdir zenml_starter
cd zenml_starter
zenml init --template starter --template-with-defaults

# Just in case, we install the requirements again
pip install -r requirements.txt
```

<details>

<summary>Above doesn't work? Here is an alternative</summary>

The starter template is the same as the [ZenML mlops starter example](https://github.com/zenml-io/zenml/tree/main/examples/mlops_starter). You can clone it like so:

```bash
git clone --depth 1 git@github.com:zenml-io/zenml.git
cd zenml/examples/mlops_starter
pip install -r requirements.txt
zenml init
```

</details>

## What you'll learn

You can either follow along in the [accompanying Jupyter notebook](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/quickstart.ipynb), or just keep reading the [README file for more instructions](https://github.com/zenml-io/zenml/blob/main/examples/quickstart/README.md).

Either way, at the end you would run three pipelines that are exemplary:

* A feature engineering pipeline that loads data and prepares it for training.
* A training pipeline that loads the preprocessed dataset and trains a model.
* A batch inference pipeline that runs predictions on the trained model with new data.

And voilà! You're now well on your way to be an MLOps expert. As a next step, try introducing the [ZenML starter template](https://github.com/zenml-io/template-starter) to your colleagues and see the benefits of a standard MLOps framework in action!

## Conclusion and next steps

This marks the end of the first chapter of your MLOps journey with ZenML. Make sure you do your own experimentation with ZenML to master the basics. When ready, move on to the [production guide](../production-guide/), which is the next part of the series.

<figure><img src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" alt="ZenML Scarf"><figcaption></figcaption></figure>
