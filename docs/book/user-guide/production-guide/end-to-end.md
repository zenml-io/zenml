---
description: Put your new knowledge in action with an end to end project
---

# An end-to-end project

In this guide, we have went over some advanced concepts:

- The value of [deploying ZenML](connect-deployed-zenml.md)
- Abstracting infrastructure configuration into [stacks](understand-stacks.md)
- [Deploying a MLOps stack](cloud-stack.md) on a cloud provider of your choice

We will now put this into action with a simple starter project.

## Get started

Start with a fresh virtual environment with no dependencies. Then let's install our dependencies:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
```

We will then use [ZenML templates](../advanced-guide/best-practices/using-project-templates.md) to help us get the code we need for the project:

```bash
mkdir zenml_starter
cd zenml_starter
zenml init --template starter --template-with-defaults

# Just in case, we install the requirements again
pip install -r requirements.txt
```

<details>

<summary>Above doesn't work? Here is an alternative</summary>

The starter template is also available as a [ZenML example](https://github.com/zenml-io/zenml/tree/main/examples/starter). You can clone it:

```bash
git clone git@github.com:zenml-io/zenml.git
cd examples/starter
pip install -r requirements.txt
zenml init
```

</details>

## Run your first pipelines

You can either follow along in the [accompanying Jupyter notebook](https://github.com/zenml-io/zenml/blob/main/examples/starter/run.ipynb), or just keep reading the [README file for more instructions](https://github.com/zenml-io/zenml/blob/main/examples/starter/run.ipynb).

Either way, at the end you would run three pipelines that are exemplary:

- A feature engineering pipeline that loads data and prepares it for training.
- A training pipeline that loads the preprocessed dataset and trains a model.
- A batch inference pipeline that runs predictions on the trained model with new data.

And voilà! You're now well on your way to be a MLOps expert. As a next step, try introducing the [ZenML starter template](https://github.com/zenml-io/template-starter) to your colleagues and see the benefits of a standard ML framework at your work.

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>