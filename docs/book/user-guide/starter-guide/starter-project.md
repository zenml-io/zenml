---
description: Put your new knowledge in action with a simple starter project
---

# A starter project

By now, you have understood some of the basic pillars of a MLOps system:

- [Pipelines and steps](create-an-ml-pipeline.md)
- [Artifacts](manage-artifacts.md)
- [Models](track-ml-models.md)

We will now put this into action with a simple starter project.

## Get started

Start with a fresh virtual environment with no dependencies. Then let's install our dependencies:

```bash
pip install "zenml[templates,server]" notebook
zenml integration install sklearn -y
```

We will then use [ZenML templates](../advanced-guide/pipelining-features/using-project-templates.md) to help us get the code we need for the project:

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

You can either follow along in the [accompanying Jupyter notebook](https://github.com/zenml-io/zenml/blob/main/examples/starter/run.ipynb), or just keep reading the docs to move forward:

```python

```

<!-- For scarf -->
<figure><img alt="ZenML Scarf" referrerpolicy="no-referrer-when-downgrade" src="https://static.scarf.sh/a.png?x-pxid=f0b4f458-0a54-4fcd-aa95-d5ee424815bc" /></figure>