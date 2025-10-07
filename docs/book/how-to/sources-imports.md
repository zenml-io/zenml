---
description: 
icon:
---

# Sources

## Source root

The **source root** is the directory which all your local imports should be relative to.

Whenever you're using ZenML, the source root will be computed as follows:
- If you're in a child directory of a [ZenML repository](https://docs.zenml.io/user-guides/best-practices/set-up-your-repository) (which you can initialize by running `zenml init`), the repository directory will be the source root. In general, we recommend also making the source root explicit by intializing a ZenML repository before running any pipelines.
- If no ZenML repository exists in your current working directory or any of the parent directories, ZenML falls back to the parent directory of the python file that you're currently executing. For example, if you're running the file `/a/b/run.py`, the source root will be `/a/b`.

{% hint style="warning" %}
If you're running in a notebook or an interactive Python environment, there will be no file that is currently executed and ZenML won't be able to automatically infer the source root. Therefore, you'll need to explicitly define the source root by initializing a ZenML repository in these cases.
{% endhint %}

## Source/Import Path

There are some places in ZenML where it expects a source (sometimes also called import path) in the configuration. Some examples are:
- When configuring hooks for steps using a config file
```yaml
success_hook_source: <SUCCESS-HOOK-SOURCE>
```
- When trying to run or deploy a pipeline using the CLI:
```bash
zenml pipeline deploy <PIPELINE-SOURCE>
```

In those cases, ZenML expects a path **relative to your source root** that can be imported in python. Let's look at a few examples:
Let's say you have the following code in a file called `/a/b/c/run.py` as follows:
```python
from zenml import pipeline

@pipeline
def my_pipeline():
    ...
```

If your source root is
- `/a/b/c`, the pipeline source would be `run.my_pipeline`
- `/a`, the pipeline source would be `b.c.run.my_pipeline` 

{% hint style="info" %}
Note that the source is not a file path, but instead its elements are separated by dots similar to how you would write import statements in Python.
{% endhint %}

## Imports when running containerized steps

When running pipeline steps in a containerized environment, ZenML will make sure (either by including them in the image or downloading them) the files inside your [source root](#source-root) are available in the container before executing your step code. To execute your step code, ZenML will import the Python module in which the step is defined. For this to work, all your imports of other local code files must be **relative to the source root**.

{% hint style="info" %}
If you don't need all files inside your source root to execute your steps, check out [this page](./containerization/containerization.md#controlling-included-files) for information on how to include/exclude certain files.
{% endhint %}